# Typeform MCP+ Server

Toolkit for managing Typeform surveys, workspaces, themes, and forms through Claude skills and a Python-based markdown-to-Typeform converter. Designed for teams that author survey content in markdown and deploy to Typeform via API.

## What's in the box

```
typeform-mcp-plus-server/
  typeform-toolkit/
    install.sh                  # One-command setup for MCP, converter, and skills
    converter/
      md_to_typeform.py         # Markdown-to-Typeform payload converter
      push_to_typeform.sh       # Push payloads to Typeform API (create or update)
      config_template.json      # Default survey configuration
    skills/
      typeform-survey-builder/  # Claude skill for building surveys from markdown
      typeform-account-manager/ # Claude skill for workspace/theme/form management
  typeform-api-reference.md     # Consolidated Typeform API + JS SDK reference
  skill_portfolio/
    PORTFOLIO_REPORT.md         # Skill extraction methodology and coverage report
    typeform-account-manager/   # Portfolio snapshot of account manager skill
    typeform-survey-builder/    # Portfolio snapshot of survey builder skill
```

## Quick start

### Prerequisites

- Python 3.8+
- A Typeform personal access token (`tfp_...`)
- Claude Code CLI (for MCP connection and skills)

### Install

```bash
git clone https://github.com/t0ddc3by/typeform-mcp--server.git
cd typeform-mcp--server

# Run the installer — connects MCP, installs converter, installs skills
chmod +x typeform-toolkit/install.sh
./typeform-toolkit/install.sh
```

The installer does four things: connects the Typeform MCP server to Claude, copies the converter toolkit to `~/typeform-toolkit/`, installs both Claude skills to `~/.claude/skills/`, and optionally exports your token to your shell profile.

### Build a survey from markdown

```bash
cd ~/typeform-toolkit

# Convert markdown to Typeform JSON payload
python3 md_to_typeform.py survey.md \
  --config config_template.json \
  --workspace "Custom Curriculum" \
  --token $TYPEFORM_TOKEN \
  --output payload.json

# Push to Typeform (creates new form)
./push_to_typeform.sh --create payload.json $TYPEFORM_TOKEN

# Or update an existing form
./push_to_typeform.sh payload.json <form_id> $TYPEFORM_TOKEN
```

The converter supports a combined convert-and-push mode:

```bash
python3 md_to_typeform.py survey.md \
  --config config_template.json \
  --workspace "Custom Curriculum" \
  --token $TYPEFORM_TOKEN \
  --output payload.json \
  --push --form-id <FORM_ID>
```

### Converter modes

| Mode | Command |
|------|---------|
| Convert only | `python3 md_to_typeform.py survey.md --config config.json --output payload.json` |
| Validate | `python3 md_to_typeform.py survey.md --validate` |
| List workspaces | `python3 md_to_typeform.py --list-workspaces --token $TYPEFORM_TOKEN` |
| Convert + push | Add `--push --form-id <ID>` to any convert command |

## Claude skills

Both skills use a hybrid MCP + REST API approach. The Typeform MCP covers read operations; the REST API handles writes that the MCP doesn't expose.

### typeform-survey-builder

Builds and deploys Typeform surveys from structured markdown documents. Handles field type mapping (`long_text`, `contact_info`, `file_upload`, `statement` dividers), brand theming, workspace targeting, validation, and single-command push.

**Use when:** Creating a new survey from markdown, updating an existing survey after content changes, converting any structured questionnaire into a live Typeform.

### typeform-account-manager

Manages Typeform account resources: workspaces (25 tracked), themes, forms, and contacts. Includes a reference table of all workspace IDs and shared status.

**Use when:** Listing or creating workspaces, updating theme properties (button shapes, colors, fonts), listing forms by workspace, managing form-to-contact property mappings.

## API reference

`typeform-api-reference.md` is a consolidated reference covering the full Typeform developer surface:

1. Platform overview (auth, rate limits, base URLs)
2. Create API (forms, fields, logic, themes, workspaces, images)
3. Responses API (retrieval, filtering, deletion)
4. Error handling and pagination
5. Webhooks API (CRUD, payload structure, HMAC signature verification)
6. Embed SDK (widget, popup, slider, popover, sidetab)
7. JavaScript SDK (`@typeform/api-client`) with full type definitions

Extracted from Typeform's developer documentation and the `@typeform/api-client` source code.

## Key implementation notes

- Typeform's PUT endpoint overwrites the entire form. Always include all fields or they get deleted.
- The `show_time_to_complete` setting is auto-calculated by Typeform based on field count/type. It can't be overridden to a custom value — disable it and add manual text to the welcome screen description instead.
- Welcome screen title styling is controlled at the theme level, not inline. Markdown and HTML in the title field render as literal text.
- Welcome screen descriptions accept plain text only. Markdown bold (`**`) and HTML (`<strong>`) render literally.
- The Typeform MCP supports reads but most write operations require direct REST API calls.
- Rate limit: 2 requests per second per account across all API endpoints.

## License

Private repository. Not for distribution.
