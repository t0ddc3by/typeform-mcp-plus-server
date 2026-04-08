---
name: typeform-response-analyzer
description: >
  Pull, structure, and analyze Typeform survey responses using the Responses API.
  Produces markdown analysis reports, CSV exports, and structured JSON. Includes
  per-question response rates, text answer collection, choice distributions, word
  count statistics, completion analytics, and timeline data. Integrates with
  status.typeform.com for pre-flight health checks. Use when analyzing survey
  results, comparing response patterns, generating reports from Typeform data,
  or exporting responses for downstream processing. Do NOT use for creating or
  editing surveys (use typeform-survey-builder), managing account resources
  (use typeform-account-manager), or real-time response processing (use webhooks).
type: workflow
tools_required:
  - Typeform REST API (curl or Python urllib)
  - Python 3
network_access: outbound_allowlist
allowed_domains:
  - api.typeform.com
  - status.typeform.com
filesystem_write: project_dir_only
---

# Typeform Response Analyzer

Pull, structure, and analyze Typeform survey responses using the Responses API. Produces markdown analysis reports, CSV exports, and structured JSON with per-question response rates, text answer collection, choice distributions, word count statistics, completion analytics, and timeline data.

Do NOT use for: creating or editing surveys (use typeform-survey-builder), managing account resources (use typeform-account-manager), or real-time response processing (use webhooks via the REST API directly).

---

## Prerequisites

- A Typeform personal access token available as `TYPEFORM_TOKEN` env var or passed via `--token`
- The response analyzer at `typeform-toolkit/converter/typeform_responses.py`
- A deployed Typeform form with at least one response

## Core Workflow

### Phase 1: Pre-Flight Check

Before pulling responses, optionally verify the platform is healthy:

```bash
python typeform_status.py --api-only
```

Or inline with the response pull:
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --check-status
```

This checks `status.typeform.com/api/v2/status.json` and warns (but doesn't block) if any Developer Platform components are degraded.

### Phase 2: Inspect Form Structure

Before pulling responses, inspect the form to understand its question structure:

```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --form-only
```

This returns the field list with types — useful for confirming you're pulling the right form and understanding what answer types to expect.

### Phase 3: Pull Responses

**All completed responses:**
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN -o report.md
```

**Responses since a date:**
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --since 2026-01-01
```

**Include partial submissions:**
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --include-partial
```

**Limit to N most recent:**
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --limit 50
```

The tool handles cursor-based pagination automatically for large response sets (up to 1,000 per page).

### Phase 4: Analyze

The analyzer computes:

| Metric | Description |
|--------|-------------|
| Completion rate | Completed vs total (including partial if requested) |
| Per-question response rate | How many respondents answered each question |
| Word count stats | Average, min, max for long_text/short_text fields |
| Choice distributions | Frequency counts with percentages for structured fields |
| Timeline | First response, last response, collection span in days |
| Section grouping | Questions organized by their survey sections |

The markdown report groups answers by section and question, shows every individual response for text fields, and renders bar-chart distributions for choice/rating/scale fields.

### Phase 5: Export

Three output formats:

**Markdown report** (default) — structured analysis with all answers, stats, and distributions:
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN -o analysis.md
```

**CSV** — one row per respondent, one column per question (for spreadsheet analysis):
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --csv -o responses.csv
```

**Structured JSON** — full analytics object for programmatic consumption:
```bash
python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --json -o data.json
```

## Working with the Output

### In-Context Analysis

After generating a markdown report, I can analyze the responses directly:

1. Look for patterns across respondents on the same question
2. Identify questions with low response rates (possible friction points)
3. Flag very short answers that may indicate disengagement
4. Compare answer themes across sections
5. Identify outlier responses that diverge from the group

### Cross-Form Comparison

Run the analyzer on multiple forms and compare:

```bash
python typeform_responses.py <FORM_A> --token $TYPEFORM_TOKEN -o cohort_a.md
python typeform_responses.py <FORM_B> --token $TYPEFORM_TOKEN -o cohort_b.md
```

Then compare the reports side by side for differences in response patterns, completion rates, and answer themes.

### Feeding Into Other Tools

- **CSV export → Excel skill** — pivot tables, charts, deeper quantitative analysis
- **Markdown report → doc-coauthoring** — polish into a findings presentation
- **JSON export → custom analysis** — programmatic processing of structured response data

## Typeform Responses API Reference

The analyzer uses these API endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET /forms/{form_id}` | Form definition (field structure, sections) |
| `GET /forms/{form_id}/responses` | Response data with pagination |

**Key parameters used:**

| Parameter | Purpose |
|-----------|---------|
| `page_size` | Up to 1000 per request |
| `since` / `until` | Date range filtering |
| `response_type` | `completed`, `partial`, `started` |
| `after` | Cursor-based pagination token |

**Important:** Very recent submissions (within ~30 minutes) may not appear via the API. The Responses API has eventual consistency — if you need real-time data, use webhooks.

## Platform Status Integration

The `typeform_status.py` utility checks `status.typeform.com` and reports:

| Mode | Command | Purpose |
|------|---------|---------|
| Summary | `python typeform_status.py` | Overall health + MCP+ critical services |
| API only | `python typeform_status.py --api-only` | Developer Platform components only |
| All | `python typeform_status.py --all` | Every component grouped by category |
| JSON | `python typeform_status.py --json` | Raw JSON for scripting |
| Check | `python typeform_status.py --check` | Exit code 0/1 for shell conditionals |

Eight services are flagged as "MCP+ critical": Create API, Responses API, Webhooks API, Developer Portal, Submit responses, Open/Load forms, Form creation, Publish form.

## SuccessCOACHING Form Reference

| Workspace | ID | Contains |
|-----------|----|----------|
| VBS Learner Reflection | `ZBfTUC` | Reflection survey forms |
| Custom Curriculum | `3gBrdH` | Customization discovery surveys |
| CS Foundations | `db4w4b` | Foundation course surveys |
| Bootcamps | `XtMDEn` | Bootcamp intake/feedback |
| SuccessCOACHING Cohorts | `tQX4QE` | Cohort surveys |
| New Courses | `9jKdMY` | Course development surveys |

To find form IDs within a workspace:
```bash
curl -s "https://api.typeform.com/forms?workspace_id=ZBfTUC&page_size=200" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data.get('items', []):
    print(f'{f[\"id\"]:12s} | {f[\"title\"]}')"
```

## Integration with Other Skills

- **typeform-survey-builder** — Creates the surveys this skill analyzes
- **typeform-account-manager** — Manages the workspaces and forms referenced here
- **data:analyze** — Deeper statistical analysis of exported response data
- **data:build-dashboard** — Interactive HTML dashboards from response analytics

## Artifacts

| File | Purpose |
|------|---------|
| `typeform_responses.py` | Response puller, analyzer, and report generator |
| `typeform_status.py` | Platform status checker (status.typeform.com) |

[PROPOSED]
