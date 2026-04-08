# Typeform MCP+ Server

Typeform's official MCP server gives Claude read access to forms, contacts, and lists. It can't create fields, edit surveys, manage workspaces, update themes, or push form payloads. That's most of what you'd want an AI assistant to do with Typeform.

This project fills those gaps. MCP+ wraps the official MCP for reads, the Typeform REST API for writes, and a Python converter pipeline for the heavy lifting of turning markdown documents into live Typeform surveys. Three Claude skills orchestrate the whole thing so you can say "build me a survey from this document," "move that form to a different workspace," or "pull and analyze the responses from that survey" and it works end to end.

## Why "MCP+"

Typeform's MCP server exposes 13 tools. Twelve of them are contact-related. The forms side is limited to four operations: create (blank shell only), get, list, and delete. There's no way to add fields, set up logic, configure welcome screens, assign themes, or target workspaces through MCP alone.

The REST API covers everything, but it's designed for machine-to-machine integration — you're building JSON payloads with nested field definitions, ref IDs, and theme hrefs. Not something you'd want Claude to improvise from scratch on every request.

MCP+ bridges the two by giving Claude structured skills that know when to use MCP (fast reads, contact operations) and when to drop to the REST API (form creation with fields, workspace management, theme updates). The converter pipeline handles the gnarliest part: transforming a readable markdown document into a fully-specified Typeform API payload with contact capture, section dividers, field validation, bold syntax conversion, and brand theming.

## How the MCP and REST API work together

The division of labor isn't arbitrary — it follows what each interface does well.

**Typeform MCP handles:**
- Listing and searching forms across workspaces (`forms-public_list_forms`)
- Retrieving full form definitions for inspection (`forms-public_get_form`)
- Creating blank form shells when a new form ID is needed (`forms-public_create_form`)
- All contact operations: creating contacts, querying segments, mapping form fields to contact properties, managing contact lists

**REST API (via curl) handles:**
- Full form creation and updates with fields, logic, screens, and settings (`PUT /forms/{id}`)
- Workspace CRUD: listing, creating, and assigning forms to workspaces
- Theme management: reading, creating, and updating themes (colors, fonts, button shapes, rounded corners)
- Response retrieval with filtering, pagination, and deletion
- Webhook configuration
- Form settings that MCP doesn't expose (progress bars, time estimates, branding toggles, meta/SEO)

**The converter pipeline handles:**
- Parsing markdown into structured survey sections, questions, and metadata
- Converting markdown bold (`**text**`) to Typeform's non-standard bold syntax (`*text*`)
- Assembling the full form payload: contact capture field, instruction screens, section dividers interleaved with questions, file upload fields, welcome/thank-you screens
- Workspace resolution by name (queries the API, matches case-insensitively, optionally creates if missing)
- Pre-push validation catching 10+ categories of errors before they hit the API
- Direct push to Typeform via `PUT` or `POST` depending on create vs. update

In practice, a typical "build a survey" workflow touches all three layers. The skill reads existing forms via MCP to check for duplicates, resolves the target workspace via REST, runs the converter to transform markdown into a payload, pushes via REST, then verifies the result with a GET through MCP.

## What's in the repo

```
typeform-mcp-plus-server/
  typeform-toolkit/
    install.sh                  # One-command setup: MCP connection, converter, skills
    converter/
      md_to_typeform.py         # Markdown → Typeform JSON converter + validator
      typeform_responses.py     # Response puller, analyzer, and report generator
      typeform_status.py        # Platform status checker (status.typeform.com)
      push_to_typeform.sh       # Push payloads to Typeform API (create or update)
      config_template.json      # Default survey configuration template
    skills/
      typeform-survey-builder/  # Claude skill: markdown → live Typeform survey
      typeform-account-manager/ # Claude skill: workspaces, themes, forms, contacts
      typeform-response-analyzer/ # Claude skill: pull, analyze, and report on responses
  templates/
    TEMPLATES.md                # Template guide: markdown conventions, config reference, settings docs
    simple-survey.md            # 3 sections, 6 questions — short feedback survey
    simple-config.json          # Config for simple template (replace placeholder IDs)
    comprehensive-assessment.md # 5 sections, 17 questions — full domain assessment
    comprehensive-config.json   # Config for comprehensive template
  typeform-api-reference.md     # 1,400-line consolidated API + JS SDK reference
  skill_portfolio/
    PORTFOLIO_REPORT.md         # Build methodology and coverage analysis
    typeform-account-manager/   # Portfolio snapshot
    typeform-survey-builder/    # Portfolio snapshot
```

## Quick start

### Prerequisites

- Python 3.8+
- A Typeform personal access token (`tfp_...`)
- Claude Code or Cowork (for MCP connection and skills)

### Install

```bash
git clone https://github.com/t0ddc3by/typeform-mcp--server.git
cd typeform-mcp--server

chmod +x typeform-toolkit/install.sh
./typeform-toolkit/install.sh
```

The installer connects the Typeform MCP server to Claude (`claude mcp add`), copies the converter toolkit to `~/typeform-toolkit/`, installs both Claude skills to `~/.claude/skills/`, and optionally exports your token to your shell profile.

### Manual MCP setup (if not using the installer)

```bash
claude mcp add typeform https://api.typeform.com/mcp \
  --transport http \
  --scope user \
  --header "Authorization: Bearer $TYPEFORM_TOKEN"
```

Argument ordering matters: name and URL are positional and must come before flags. Reversing them causes a silent failure.

## The three Claude skills

### typeform-survey-builder

End-to-end workflow for building and deploying Typeform surveys from structured markdown. This is the skill that does most of the heavy lifting.

The workflow runs in five phases: prepare config (workspace targeting, theme selection, contact fields) → parse and convert (markdown to Typeform JSON payload) → validate (10+ error categories caught before push) → push to Typeform (create or update via REST API) → verify (GET the live form and confirm field count, first field type, workspace assignment).

What it handles that raw MCP can't:
- Field type mapping: markdown questions become `long_text` fields, sections become `statement` dividers, the first field is always `contact_info` with configurable subfields, and the last field is `file_upload` for document attachments
- Bold syntax conversion: standard markdown `**bold**` doesn't work in Typeform (renders literally). The converter transforms it to Typeform's `*bold*` format automatically
- Workspace targeting: resolve by name, by href, or create-on-demand
- Welcome and thank-you screen configuration with custom text, buttons, and redirect URLs
- Brand theming: theme assignment, branding toggle, autosave, progress bar settings
- Validation catching double-asterisk bugs, missing contact fields, numbering gaps, title length issues, and click-fatigue ratios before anything hits the API

**Trigger:** "Build a survey from this markdown," "push this survey to Typeform," "convert this document to a Typeform."

### typeform-account-manager

Infrastructure management for the Typeform account — everything that isn't survey content authoring.

This skill maintains a reference table of all 25 workspaces (IDs, names, shared status) so Claude doesn't need to query the API for lookups. For operations the MCP can handle (listing forms, reading form definitions, contact management), it uses MCP directly. For everything else (workspace creation, theme updates, form settings changes), it drops to curl against the REST API.

What it covers:
- Workspace operations: list all, create new, move forms between workspaces
- Theme management: read current theme, update colors/fonts/button shapes/rounded corners. Theme updates affect all forms using that theme — the skill warns about this.
- Form listing and filtering by workspace
- Contact-to-form field mapping: check which form fields can map to contact properties, create mappings, verify they took
- Form settings updates that require REST: `show_time_to_complete`, `show_typeform_branding`, welcome screen text, meta/SEO fields

**Trigger:** "List my workspaces," "update the button shape to capsule," "map this form's contact fields," "move this form to the Custom Curriculum workspace."

### typeform-response-analyzer

Pulls responses from the Typeform Responses API, structures them by section and question, and generates analysis reports. Three output formats: markdown report (structured analysis with every individual response, per-question statistics, and distributions), CSV (one row per respondent for spreadsheet analysis), and structured JSON (for programmatic consumption).

What it computes:
- Completion rate and per-question response rates (spots friction points where respondents drop off)
- Word count statistics for open-text questions (average, min, max — identifies thin vs. substantive answers)
- Choice distributions with visual bar charts for rating, scale, and multiple-choice fields
- Collection timeline: first response, last response, span in days
- Section-grouped analysis following the survey's own structure

The analyzer handles cursor-based pagination automatically for large response sets. It can filter by date range, include partial submissions, and limit to the N most recent responses.

Includes a pre-flight integration with `status.typeform.com` — before pulling responses, you can check whether the Responses API is healthy. The status checker reports on 8 MCP+ critical services and surfaces any active incidents.

**Trigger:** "Analyze the responses from this survey," "pull the results from form XYZ," "export survey responses as CSV," "is Typeform up right now?"

## Platform status checker

`typeform_status.py` monitors Typeform's platform health by querying `status.typeform.com/api/v2/`. It tracks 36 components across 10 groups and flags 8 services as "MCP+ critical" — the ones that directly affect toolkit operations.

```bash
python3 typeform_status.py              # Quick summary
python3 typeform_status.py --api-only   # Developer Platform only
python3 typeform_status.py --all        # Every component
python3 typeform_status.py --check      # Exit code 0 if healthy, 1 if degraded
```

The response analyzer integrates this — pass `--check-status` to any response pull and it verifies the API is up before making requests.

## The converter pipeline

`md_to_typeform.py` is a standalone Python CLI that does the markdown-to-Typeform transformation without requiring Claude or MCP. It has four modes:

| Mode | Command |
|------|---------|
| Convert | `python3 md_to_typeform.py survey.md --config config.json --output payload.json` |
| Validate only | `python3 md_to_typeform.py survey.md --config config.json --validate-only` |
| List workspaces | `python3 md_to_typeform.py --list-workspaces --token $TYPEFORM_TOKEN` |
| Convert + push | Add `--push --form-id <ID> --token $TYPEFORM_TOKEN` to any convert command |

### Markdown conventions

The converter expects this structure:

```markdown
# Survey Title
Preamble text becomes the welcome screen description.

## How to Approach This
Instructions text becomes a statement screen after contact capture.

## Section 1: Topic Name
Statement screen divider.

**1.1** First question text
→ long_text field

**1.2** Second question text
→ long_text field

## Section 2: Another Topic

**2.1** More questions...

Upload any relevant documents below.
→ file_upload field (always last)
```

### Config template

The JSON config controls everything the markdown doesn't: workspace targeting, theme, contact field selection, welcome/thank-you screen copy, branding settings, and meta tags. See `config_template.json` for the full schema.

### Validation checks

| Check | Severity |
|-------|----------|
| Double-asterisk `**bold**` surviving in field titles | ERROR |
| Missing `contact_info` as first field | ERROR |
| Missing workspace reference | ERROR |
| Missing theme or account ID | ERROR |
| Non-required questions when `all_required: true` | ERROR |
| Question numbering gaps (e.g., 2.3 missing) | WARN |
| Title exceeds 300 characters | WARN |
| Low question-to-statement ratio (click fatigue) | WARN |
| Missing instructions screen | WARN |

## API reference

`typeform-api-reference.md` is a 1,400-line consolidated reference extracted from Typeform's developer documentation and the `@typeform/api-client` npm package source. Eight sections:

1. **Platform overview** — Auth (bearer tokens, OAuth), rate limits (2 req/sec/account), base URLs (standard + EU)
2. **Create API** — Forms (23 field types, welcome/thank-you screens, logic jumps, variables), themes (32 fonts, colors, button styles), workspaces, images
3. **Responses API** — Retrieval with date/cursor filtering, response deletion, answer type reference
4. **Error handling and pagination** — Error codes, page-based and cursor-based pagination
5. **Webhooks API** — CRUD operations, payload structure with field-level answer data, HMAC SHA-256 signature verification
6. **Embed SDK** — 5 embed types (widget, popup, slider, popover, sidetab), vanilla JS and React, configuration properties, callbacks, URL parameters
7. **JavaScript SDK** — Full `@typeform/api-client` documentation: all 7 resource namespaces (forms, images, themes, workspaces, responses, webhooks, insights), auto-pagination internals, PATCH path whitelist, error handling
8. **Type definitions** — Every enum, interface, and union type from the SDK: field types, fonts, languages, condition operators, logic actions, form settings, custom message keys, notification templates, currency options

## Templates

The `templates/` directory contains tested markdown surveys and matching config files. Each template validates against the converter with zero errors.

| Template | Sections | Questions | Use case |
|----------|----------|-----------|----------|
| `simple-survey.md` | 3 | 6 | Short feedback surveys, intake forms, post-meeting follow-ups |
| `comprehensive-assessment.md` | 5 | 17 | Multi-section assessments covering an entire domain |

Each template ships with a config JSON. Replace the placeholder IDs (`YOUR_WORKSPACE_ID`, `YOUR_THEME_ID`, `YOUR_ACCOUNT_ID`) with your own values.

See `templates/TEMPLATES.md` for the full guide on writing your own survey markdown, config field reference, and documentation of all converter-applied settings.

### Key authoring rules

**Question numbering:** Use double asterisks around the number — `**1.1** Question text`. The converter transforms `**1.1**` into Typeform's non-standard bold syntax `*1.1*`. Typeform's auto-numbering is disabled by default to prevent double-numbered questions.

**Bold text:** Standard markdown `**bold**` renders as literal asterisks in Typeform. The converter converts all `**text**` to `*text*` automatically. Don't use single asterisks in your source markdown.

**Section headers:** Every `## Section N: Title` becomes a statement screen (section divider). Aim for 2-3+ questions per section to avoid click fatigue.

**File uploads:** End your survey with a paragraph mentioning uploads or documents — the converter creates a non-required `file_upload` field from it.

## Converter settings

The converter applies sensible defaults for settings that commonly cause problems. These are hardcoded and don't appear in the config file:

| Setting | Value | Rationale |
|---------|-------|-----------|
| `show_question_number` | `false` | Typeform's auto-numbering (1, 2, 3...) conflicts with manual `*1.1*` style. Disabling prevents double-numbering. |
| `show_time_to_complete` | `false` | Typeform auto-calculates this and doesn't allow customization. The estimate is often inaccurate for long-text heavy surveys. Add time guidance to your welcome screen text instead. |
| `type` | `quiz` | Enables the progress bar without requiring scoring or grading. |
| `show_key_hint_on_choices` | `false` | Keyboard shortcut hints aren't relevant when fields are primarily `long_text`. |
| `are_uploads_public` | `false` | Uploaded files require authentication. |
| `allow_indexing` | `false` | Surveys not discoverable by search engines. |

To override any of these after deployment, use `PUT /forms/{form_id}` via the REST API or the typeform-account-manager skill.

## Beyond basic surveys: what else MCP+ can do

The converter handles the markdown-to-Typeform pipeline, but the REST API and MCP together expose a much broader set of capabilities. These are operations you can perform through the skills or directly via API — they don't require converter changes.

### Response analytics and data export

Retrieve all responses with filtering by date range, completion status, or specific fields. The Responses API supports cursor-based pagination for large datasets (up to 1,000 responses per page), filtering for `completed`, `partial`, or `started` responses, and full-text search across all answers and hidden fields. Use this for post-survey analysis, CRM integration, or feeding response data into downstream workflows.

### Contact pipeline

The Typeform MCP handles contact operations natively — create contacts, query segments, and map form fields to contact properties. After a survey is live, you can map `contact_info` subfields (first name, last name, email, company) to your Contacts database so that every submission automatically populates a contact record. The account-manager skill walks through the compatibility check, mapping creation, and verification.

### Webhooks for real-time processing

Configure webhooks to push response data to any HTTPS endpoint the moment a form is submitted. Payloads include the full response with field-level answer data, calculated scores, hidden fields, and variables. Typeform signs payloads with HMAC SHA-256 for verification. Useful for triggering Slack notifications, updating CRM records, starting onboarding workflows, or feeding response data into analytics pipelines.

### Logic jumps and branching

The API supports conditional logic that routes respondents to different questions based on their answers. Logic jumps use a condition → action model with operators for equality, comparison, string matching, and date ranges. Actions can jump to a specific field, thank-you screen, or outcome. Building logic jumps requires POST/PUT against the form definition — the MCP can't do this, but the REST API handles it.

### Additional field types

The converter currently produces four field types (`contact_info`, `statement`, `long_text`, `file_upload`). The API supports 23 field types total. If your survey needs structured responses beyond open-text, these are available through direct API calls or future converter extensions:

| Field type | Good for |
|------------|----------|
| `multiple_choice` | Predefined answer sets, single or multi-select |
| `rating` / `opinion_scale` | Satisfaction scores, NPS, Likert scales (5–11 steps, 16 icon shapes) |
| `yes_no` | Binary questions |
| `dropdown` | Large option lists with alphabetical sorting |
| `number` | Numeric inputs with min/max validation |
| `date` | Date collection with configurable format |
| `ranking` | Priority ordering of items |
| `email` / `website` / `phone_number` | Validated format inputs |
| `picture_choice` | Visual option selection with images |
| `matrix` | Grid-style questions (rows × columns) |
| `nps` | Net Promoter Score (0–10 scale) |
| `payment` | Stripe-integrated payment collection |
| `calendly` | Scheduling integration |
| `multi_format` | Audio, video, or text responses |

### Scoring and quizzes

Fields can carry scoring definitions — assign point values to choices and Typeform tracks calculated scores across the form. Two scoring types are supported: `boolean_correct` (true/false with a score) and `choices_all_correct` (set of correct choices with a score). Scores flow through to the Responses API and webhooks for automated grading.

### Hidden fields and URL parameters

Pass data into a form via URL parameters or the Embed SDK's `hidden` config. Hidden field values appear in response data alongside answers — useful for tracking lead source, campaign ID, account name, or any context from the referring page. The Embed SDK also supports transitive search params that forward host page query parameters directly into the form.

### Embed SDK integration

Five embed types are available: widget (inline), popup (full-screen modal), slider (side panel), popover (floating button), and sidetab (fixed side tab). Available as vanilla JavaScript functions or React components. Configuration includes auto-open triggers (page load, exit intent, scroll percentage, time delay), hidden field passthrough, callback hooks (onReady, onSubmit, onQuestionChanged), and sandbox mode for testing without recording submissions.

### Theme management

Create and update themes programmatically — colors (question, answer, button, background), font selection (any Google Font), button styling (transparent, rounded corners), field alignment, and screen font sizes. Theme updates are global: changing a theme affects every form that references it.

## Things that bit us (so they don't bite you)

**PUT overwrites everything.** Typeform's `PUT /forms/{id}` replaces the entire form definition. If you send a payload missing fields, those fields are deleted from the live form. The converter always produces a complete payload. If you're editing manually, GET the form first and modify the full response.

**Bold syntax is non-standard.** Typeform uses single asterisks `*text*` for bold, not double `**text**`. Standard markdown bold renders as literal asterisks in the form. The converter handles the conversion, but manual edits can reintroduce the bug.

**`show_time_to_complete` can't be customized.** The time estimate displayed on welcome screens is auto-calculated by Typeform based on field count and type. You can't set it to a specific value. To show "Expected time: ~30 minutes," disable the auto-estimate and add the text to the welcome screen description manually.

**Welcome screens don't support rich text.** The title field is styled by the theme (font size, weight) — not by inline markup. Both markdown and HTML render as literal characters. The description field is plain text only.

**Theme updates are global.** A theme is shared across all forms that reference it. Updating the SuccessHacker theme's button color changes every form in the account that uses it.

**`rounded_corners` has no "capsule" value.** The options are `none`, `small`, and `large`. Setting `large` produces the capsule/pill-shaped buttons.

**PUT responses are immediate; GET is eventually consistent.** After a PUT, the API response body reflects the update. But a GET issued immediately after may return stale data. Wait a few seconds if verification shows the old form state.

**MCP argument ordering.** When running `claude mcp add`, positional args (name, URL) must precede flags (`--transport`, `--header`). Reversed ordering silently fails with "missing required argument."

## License

Private repository. Not for distribution.
