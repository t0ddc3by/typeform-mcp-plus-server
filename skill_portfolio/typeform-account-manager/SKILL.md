# Typeform Account Manager

Manage Typeform account resources — workspaces, themes, forms, and contacts — using the Typeform REST API and MCP. Use when listing or creating workspaces, updating theme properties (button shapes, colors, fonts), listing forms by workspace, managing form-to-contact property mappings, or performing any Typeform admin operation that isn't survey content authoring.

Do NOT use for: building survey content from markdown (use typeform-survey-builder), editing individual form responses, or Typeform webhook/integration configuration.

---

## Prerequisites

- Typeform MCP connected OR a personal access token
- Account ID: `01D8JV3FRJBSKF0ZBM0XB0Z924` (SuccessCOACHING)

## MCP Setup

```bash
claude mcp add typeform https://api.typeform.com/mcp \
  --transport http \
  --scope user \
  --header "Authorization: Bearer <TOKEN>"
```

**Argument ordering matters**: name and URL are positional and must come before `--transport`, `--header`, and other flags. Reversing the order causes a silent failure with "missing required argument."

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `forms-public_create_form` | Create a blank form in a workspace |
| `forms-public_get_form` | Retrieve full form definition |
| `forms-public_list_forms` | List/search forms (filter by workspace, title) |
| `forms-public_delete_form` | Delete a form |
| `contacts-public_create_contact` | Add a contact to the database |
| `contacts-public_list_contacts` | Query contacts with filters |
| `contacts-public_update_contact` | Update contact properties |
| `contacts-public_create_contacts_list` | Create a contact segment |
| `contacts-public_list_contacts_lists` | List all contact segments |
| `contacts-public_get_form_property_compatibility` | Check which form fields can map to which contact properties |
| `contacts-public_create_form_property_mappings` | Map form fields → contact properties |
| `contacts-public_get_form_property_mappings` | View existing form-to-contact mappings |
| `contacts-public_list_form_property_mappings` | List all form property mappings |

**MCP does NOT support**: field-level form editing, workspace CRUD, theme updates, or response retrieval. These require the REST API.

## Core Workflows

### Workspace Operations

**List all workspaces:**
```bash
curl -s "https://api.typeform.com/workspaces" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN" | python3 -m json.tool
```

Or via the converter utility:
```bash
python md_to_typeform.py --list-workspaces --token $TYPEFORM_TOKEN
```

**Create a workspace:**
```bash
curl -s -X POST "https://api.typeform.com/workspaces" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Workspace Name"}'
```

**Move a form to a different workspace** (via PUT on the form):
Include `"workspace": {"href": "https://api.typeform.com/workspaces/<ID>"}` in the form PUT payload. The workspace assignment is part of the form definition, not a separate API call.

### Theme Operations

**Get current theme:**
```bash
curl -s "https://api.typeform.com/themes/<THEME_ID>" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN"
```

**Update theme** (e.g., button shape to capsule):
```bash
curl -s -X PUT "https://api.typeform.com/themes/<THEME_ID>" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "font": "Poppins",
    "name": "SuccessHacker",
    "has_transparent_button": false,
    "colors": {
      "question": "#111111",
      "answer": "#111111",
      "button": "#34A7D3",
      "button_content": "#FFFFFF",
      "background": "#FFFFFF"
    },
    "screens": {"font_size": "x-small", "alignment": "center"},
    "fields": {"font_size": "medium", "alignment": "left"},
    "rounded_corners": "large"
  }'
```

**Theme property reference:**

| Property | Values | Notes |
|----------|--------|-------|
| `rounded_corners` | `none`, `small`, `large` | `large` = capsule buttons. No `full` value exists. |
| `has_transparent_button` | `true`, `false` | Transparent vs solid button fill |
| `font` | Any Google Font name | SuccessCOACHING uses Poppins |
| `colors.button` | Hex color | SuccessCOACHING: `#34A7D3` |
| `screens.font_size` | `x-small`, `small`, `medium`, `large` | Welcome/thankyou screen text |
| `screens.alignment` | `left`, `center`, `right` | Welcome/thankyou screen layout |
| `fields.font_size` | `x-small`, `small`, `medium`, `large` | Question text size |
| `fields.alignment` | `left`, `center`, `right` | Question layout |

**Theme is shared**: Updating a theme affects ALL forms using it. The SuccessHacker theme (`1eNl5J`) is used across the account.

### Form Listing by Workspace

**Via MCP:**
Use `forms-public_list_forms` with `workspace_id` parameter.

**Via REST:**
```bash
curl -s "https://api.typeform.com/forms?workspace_id=<WS_ID>&page_size=200" \
  -H "Authorization: Bearer $TYPEFORM_TOKEN"
```

### Contact-to-Form Mapping

When a form uses `contact_info` fields, map them to the Contacts database:

1. **Check compatibility**: Use `contacts-public_get_form_property_compatibility` with the form_id to see which fields can map to which contact properties.
2. **Create mapping**: Use `contacts-public_create_form_property_mappings` with the form_id and property-to-field pairs.
3. **Verify**: Use `contacts-public_get_form_property_mappings` to confirm the mapping took.

## SuccessCOACHING Account Reference

| Resource | ID / Href |
|----------|-----------|
| Account | `01D8JV3FRJBSKF0ZBM0XB0Z924` |
| Theme (SuccessHacker) | `1eNl5J` — Poppins, #34A7D3, capsule buttons |
| Workspace: Custom Curriculum | `3gBrdH` |
| Workspace: CS Foundations | `db4w4b` |
| Workspace: Bootcamps | `XtMDEn` |
| Workspace: SuccessCOACHING Cohorts | `tQX4QE` |
| Workspace: New Courses | `9jKdMY` |
| Workspace: VBS Learner Reflection | `ZBfTUC` |

## Integration with Other Skills

- **typeform-survey-builder** — The survey content workflow; this skill handles the infrastructure that supports it
- **design:design-critique** — Review survey UX after creation

## Self-Documentation

| Attribute | Value |
|-----------|-------|
| Skill name | typeform-account-manager |
| Type | composite |
| Source conversation | Typeform Survey Build session (2026-04-06) |
| Tools required | Typeform MCP, Typeform REST API (curl) |
| Duration | 5-10 min per operation |
| Network access | outbound_allowlist (api.typeform.com) |
| Filesystem write | none |

[PROPOSED]
