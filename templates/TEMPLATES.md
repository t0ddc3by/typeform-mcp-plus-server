# Survey Template Guide

This directory contains tested markdown templates and their matching config files. Each template has been validated against the converter with zero errors.

## Included templates

**simple-survey.md** + **simple-config.json** — 3 sections, 6 questions. Good starting point for short feedback surveys, intake forms, or post-meeting follow-ups. Uses 3 contact fields (first name, last name, email).

**comprehensive-assessment.md** + **comprehensive-config.json** — 5 sections, 17 questions. Multi-section assessment covering an entire domain. Uses 4 contact fields (first name, last name, company, email). Includes file upload prompt at the end.

## Writing your own survey markdown

The converter parses markdown using specific patterns. Follow these rules and your surveys will convert cleanly on the first pass.

### Structure

```markdown
# Survey Title
Preamble text here — becomes the welcome screen description.

## How to Approach This
Instructions text — appears as a statement screen after the contact capture field.

## Section 1: First Topic
Optional description text under the section header — becomes the statement screen body.

**1.1** First question in this section?

**1.2** Second question in this section?

## Section 2: Second Topic

**2.1** First question in the second section?

Upload any supporting documents below.
```

### What each pattern becomes

| Markdown pattern | Typeform field type | Notes |
|---|---|---|
| `# Title` | Form title | Config `title` overrides this if set |
| Text before first `##` | Welcome screen description | Plain text only — no markdown rendering |
| `## How to Approach This` | `statement` field | Matched by exact header text |
| `## Section N: Title` | `statement` field | Section divider in the form |
| `**N.N** Question text` | `long_text` field | Number gets bold formatting: `*N.N*` |
| Last paragraph mentioning upload/documents | `file_upload` field | Always placed last |

### Question numbering

Use **double asterisks** around the number in your markdown source:

```markdown
**1.1** What is your current process?
**1.2** How do you measure success?
```

The converter transforms `**1.1**` into Typeform's bold syntax `*1.1*` automatically. The numbers appear bold in the live form.

Typeform's auto-numbering (`show_question_number`) is disabled by default in the converter — if it were enabled, Typeform would add sequential numbers (1, 2, 3...) in front of your `*1.1*` numbers, producing duplicated numbering like "3. *1.1* What is your current process?"

### Bold text in questions

Standard markdown bold (`**bold**`) doesn't render in Typeform — it shows as literal asterisks. The converter handles the conversion for you:

```
Markdown source:  **1.1** What **metrics** do you track?
Typeform output:  *1.1* What *metrics* do you track?
```

Don't use single asterisks in your source markdown. Write standard `**bold**` and let the converter translate.

### Section headers

Every `## Section N: Title` header creates a statement screen (section divider) in the form. The text below the header becomes the statement description.

If your survey has many short sections with few questions each, the converter will warn about "click fatigue" — respondents clicking through too many statement screens relative to actual questions. Aim for at least 2-3 questions per section.

### File uploads

The converter detects the last paragraph in your markdown that references uploads, documents, or files, and creates a `file_upload` field. Include something like:

```markdown
If you have supporting documents, please upload them below.
```

This field is always non-required regardless of the `all_required` config setting.

## Config file reference

The JSON config controls everything the markdown doesn't. All fields are optional except `workspace_href` (or `workspace_name`) and `theme_href`.

| Field | Purpose | Default |
|---|---|---|
| `title` | Form title (overrides `# Title` from markdown) | From markdown |
| `workspace_name` | Target workspace by name (case-insensitive match) | — |
| `workspace_href` | Target workspace by API href (skips name resolution) | — |
| `create_workspace` | Create workspace if name doesn't match | `false` |
| `theme_href` | Theme API href | — |
| `account_id` | Typeform account ID | — |
| `form_id` | Existing form ID for updates (null for new forms) | `null` |
| `contact_fields` | Array: `first_name`, `last_name`, `company`, `email`, `phone_number` | All four |
| `contact_prompt` | Text shown above contact fields | "Before we begin..." |
| `instructions_title` | Header for instructions screen | "How to Approach This" |
| `instructions_text` | Override for instructions body (empty = use markdown) | — |
| `all_required` | Make all questions required | `true` |
| `keep_subsections` | Include `###` subsections as statement screens | `false` |
| `show_typeform_branding` | Show Typeform logo | `false` |
| `autosave` | Enable client-side progress saving | `true` |
| `welcome_description` | Override welcome screen body (empty = use markdown preamble) | — |
| `welcome_button_text` | Welcome screen button | "Start Survey" |
| `thankyou_title` | Thank-you screen heading | — |
| `thankyou_description` | Thank-you screen body | — |
| `thankyou_redirect_url` | Redirect URL after completion | — |
| `thankyou_button_text` | Thank-you screen button | — |
| `meta_title` | SEO title | "{title} \| SuccessCOACHING" |
| `meta_description` | SEO description | First 160 chars of welcome text |

## Settings applied by the converter

These settings are hardcoded in the converter and don't appear in the config file. They reflect lessons learned from production deployments:

| Setting | Value | Why |
|---|---|---|
| `show_question_number` | `false` | Prevents Typeform's auto-numbering from conflicting with manual `*1.1*` style numbers |
| `show_time_to_complete` | `false` | Typeform auto-calculates this and can't be customized; add time estimates to your welcome screen text instead |
| `progress_bar` | `proportion` | Shows "X of Y" rather than percentage |
| `show_progress_bar` | `true` | Respondents see progress |
| `hide_navigation` | `false` | Back/forward arrows visible |
| `show_key_hint_on_choices` | `false` | No keyboard shortcut hints (surveys are primarily long_text) |
| `are_uploads_public` | `false` | Uploaded files require authentication to access |
| `allow_indexing` | `false` | Forms not indexed by search engines |
| `type` | `quiz` | Enables progress tracking without requiring scoring |

If you need to override any of these after deployment, use the Typeform API or the typeform-account-manager skill to update form settings directly.
