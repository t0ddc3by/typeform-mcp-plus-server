# Typeform MCP+ Server

Typeform's official MCP server gives Claude read access to forms, contacts, and lists. It can't create fields, edit surveys, manage workspaces, update themes, or push form payloads. That's most of what you'd want an AI assistant to do with Typeform.

This project fills those gaps. MCP+ wraps the official MCP for reads, the Typeform REST API for writes, and a Python converter pipeline for the heavy lifting of turning markdown documents into live Typeform surveys. Two Claude skills orchestrate the whole thing so you can say "build me a survey from this document" or "move that form to a different workspace" and it works end to end.

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
      push_to_typeform.sh       # Push payloads to Typeform API (create or update)
      config_template.json      # Default survey configuration template
    skills/
      typeform-survey-builder/  # Claude skill: markdown → live Typeform survey
      typeform-account-manager/ # Claude skill: workspaces, themes, forms, contacts
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

## The two Claude skills

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
