# Typeform Survey Builder

Build and deploy Typeform surveys from structured markdown documents using the Typeform REST API and MCP, with brand theming, workspace targeting, validation, and single-command push. Use when creating a new Typeform survey from a markdown source document, updating an existing survey after content changes, or converting any structured questionnaire into a live Typeform with SuccessCOACHING (or custom) branding.

Do NOT use for: Typeform account administration without a survey build (use typeform-account-manager), editing individual form responses, or managing Typeform integrations/webhooks.

---

## Prerequisites

- Typeform MCP connected (`claude mcp add typeform https://api.typeform.com/mcp --transport http --scope user --header "Authorization: Bearer <TOKEN>"`)
- OR a Typeform personal access token available as `TYPEFORM_TOKEN` env var or passed via `--token`
- The converter toolkit at `typeform_survey_builder/md_to_typeform.py` (produced by this conversation)
- A markdown survey document following the conventions below

## Markdown Source Conventions

The converter parses markdown with these patterns:

| Pattern | Maps to |
|---------|---------|
| `# Title` | Form title (if not overridden in config) |
| Lines before first `##` | Welcome screen description (preamble) |
| `## How to Approach This` | Instructions statement screen (after contact capture) |
| `## Section N: Title` | Statement screen (section divider) |
| `### Subsection Title` | Ignored by default; use `--keep-subsections` to include |
| `**N.N** Question text` | `long_text` question field with Typeform bold `*N.N*` |
| End-of-document upload reference | `file_upload` field (always last) |

## Core Workflow

### Phase 1: Prepare Config

I will create or update a JSON config file with these required fields:

```json
{
  "title": "Survey Title",
  "workspace_name": "Target Workspace",
  "create_workspace": false,
  "theme_href": "https://api.typeform.com/themes/<ID>",
  "account_id": "<ACCOUNT_ID>",
  "contact_fields": ["first_name", "last_name", "company", "email"],
  "all_required": true
}
```

**Workspace targeting** — three modes:
1. `workspace_name` — resolves by name at build time (case-insensitive match)
2. `workspace_href` — direct API href (skips resolution)
3. `--create-workspace` flag — creates the workspace if the name doesn't match

To discover available workspaces:
```bash
python md_to_typeform.py --list-workspaces --token $TYPEFORM_TOKEN
```

### Phase 2: Parse and Convert

I will run the converter, which:
1. Parses the markdown into sections, questions, preamble, and instructions
2. Converts `**bold**` markdown to Typeform's `*bold*` syntax
3. Builds the contact_info field as the first field (with configured subfields)
4. Inserts the "How to Approach This" instructions as the second field
5. Interleaves section dividers (statement screens) with their questions
6. Appends document upload prompt + file_upload field at the end
7. Assembles welcome screen, thank-you screen, theme, workspace, and settings

```bash
python md_to_typeform.py survey.md \
  --config config.json \
  --output payload.json \
  --workspace "Custom Curriculum" \
  --token $TYPEFORM_TOKEN
```

### Phase 3: Validate

The built-in validator checks for:

| Check | Severity |
|-------|----------|
| Double-asterisk `**bold**` in titles (won't render in Typeform) | ERROR |
| Missing contact_info field | ERROR |
| Contact capture not first field | WARN |
| Missing "How to Approach This" instructions | WARN |
| Question numbering gaps (e.g., 2.3 missing before 2.4) | WARN |
| Non-required questions when `all_required: true` | ERROR |
| Title length > 300 chars | WARN |
| Low question-to-statement ratio (click fatigue) | WARN |
| Missing workspace_href or workspace_name | ERROR |
| Missing theme_href or account_id | ERROR |

Validate without producing output:
```bash
python md_to_typeform.py survey.md --config config.json --validate-only
```

### Phase 4: Push to Typeform

**Update existing form:**
```bash
python md_to_typeform.py survey.md \
  --config config.json \
  --output payload.json \
  --push --form-id <FORM_ID> \
  --token $TYPEFORM_TOKEN
```

**Create new form** (via shell script):
```bash
./push_to_typeform.sh --create payload.json $TYPEFORM_TOKEN
```

**Update existing form** (via shell script):
```bash
./push_to_typeform.sh payload.json <FORM_ID> $TYPEFORM_TOKEN
```

### Phase 5: Verify

After pushing, I will verify the form state by:
1. GET the form via API and confirm field count matches payload
2. Check that the first field is `contact_info`
3. Confirm zero double-asterisk occurrences in field titles
4. Confirm welcome screen has no unexpected attachments
5. Verify workspace assignment matches target

```bash
curl -s "https://api.typeform.com/forms/<FORM_ID>" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN" | python3 -c "
import json, sys
d = json.load(sys.stdin)
f = d.get('fields', [])
print(f'Fields: {len(f)}')
print(f'First field type: {f[0][\"type\"] if f else \"none\"}')
print(f'Double-asterisks: {sum(1 for x in f if \"**\" in x.get(\"title\",\"\"))}')
print(f'Workspace: {d.get(\"workspace\",{}).get(\"href\",\"unknown\")}')
"
```

## Typeform API Gotchas (Learned from This Build)

1. **Bold syntax**: Typeform uses single `*text*` for bold, NOT double `**text**` like standard markdown. The converter handles this, but manual edits can reintroduce the bug.

2. **PUT eventual consistency**: After a PUT, a GET may briefly return stale data. If verification shows the old form, wait 5 seconds and re-check. The API response body from PUT itself always reflects the update.

3. **MCP limitations**: The Typeform MCP supports `create_form`, `get_form`, `list_forms`, `delete_form`, and contact operations — but NOT field-level editing. Full form definition requires `PUT /forms/{id}` via REST API (curl).

4. **Theme `rounded_corners`**: Only accepts `none`, `small`, `large` — there is no `full` or `capsule` value. `large` produces the capsule/pill shape.

5. **`claude mcp add` argument ordering**: Positional args (name, URL) must come before flags (`--transport`, `--header`). Reversed ordering silently fails.

6. **Form type**: Use `"type": "quiz"` for surveys with progress tracking. Despite the name, it doesn't require scoring.

## SuccessCOACHING Brand Defaults

| Setting | Value |
|---------|-------|
| Theme | `https://api.typeform.com/themes/1eNl5J` (SuccessHacker — Poppins, #34A7D3 buttons) |
| Account ID | `01D8JV3FRJBSKF0ZBM0XB0Z924` |
| Logo | `https://images.typeform.com/images/QezRTiRQVQte` |
| Button shape | `rounded_corners: large` (capsule) |
| Branding | `show_typeform_branding: false` |
| Welcome screen | Text-only centered (no logo attachment — light brand presence) |

## Artifacts

| File | Purpose |
|------|---------|
| `md_to_typeform.py` | Converter + validator CLI |
| `config_template.json` | Pre-filled config for SuccessCOACHING surveys |
| `push_to_typeform.sh` | Shell wrapper for create/update via curl |

## Integration with Other Skills

- **typeform-account-manager** — Use before this skill to set up workspaces and themes
- **design:design-critique** — Use after pushing to review survey UX quality
- **structural-template-analyzer** — Use to reverse-engineer markdown patterns from existing survey documents

## Self-Documentation

| Attribute | Value |
|-----------|-------|
| Skill name | typeform-survey-builder |
| Type | workflow |
| Source conversation | Typeform Survey Build session (2026-04-06) |
| Tools required | Typeform MCP, Typeform REST API (curl), Python 3 |
| Duration | 15-30 min per survey |
| Network access | outbound_allowlist (api.typeform.com) |
| Filesystem write | project_dir_only |

[PROPOSED]
