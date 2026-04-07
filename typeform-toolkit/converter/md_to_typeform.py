#!/usr/bin/env python3
"""
Markdown-to-Typeform Survey Converter
======================================
Parses a structured markdown survey document and produces a validated
Typeform API JSON payload ready for PUT /forms/{form_id}.

Usage:
    python md_to_typeform.py survey.md --config survey_config.json --output payload.json

The config file specifies: form title, workspace, theme, contact fields,
instructions text, and brand settings.

Markdown conventions:
    ## Section N: Title         → statement screen (section divider)
    ### Subsection Title        → ignored by default (use --keep-subsections to include)
    **N.N** Question text       → long_text question field
    Lines before first ##       → treated as preamble (welcome screen description)
"""

import json
import re
import sys
import uuid
import argparse
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


# ── Data classes ──

@dataclass
class SurveyConfig:
    """Configuration for a Typeform survey build."""
    title: str
    workspace_href: str
    theme_href: str
    account_id: str
    form_id: Optional[str] = None  # If updating an existing form
    workspace_name: str = ""       # Resolve workspace by name (overrides workspace_href)
    create_workspace: bool = False # Create workspace if it doesn't exist
    # Contact capture
    contact_fields: list = field(default_factory=lambda: [
        "first_name", "last_name", "company", "email"
    ])
    contact_prompt: str = "Before we begin, please tell us who you are."
    # Instructions
    instructions_title: str = "How to Approach This"
    instructions_text: str = ""
    # Settings
    all_required: bool = True
    keep_subsections: bool = False
    show_typeform_branding: bool = False
    autosave: bool = True
    # Welcome screen
    welcome_description: str = ""
    welcome_button_text: str = "Start Survey"
    # Thank you screen
    thankyou_title: str = "Thank you for investing the time."
    thankyou_description: str = ""
    thankyou_redirect_url: str = ""
    thankyou_button_text: str = ""
    # Meta
    meta_title: str = ""
    meta_description: str = ""


@dataclass
class ParsedQuestion:
    """A question extracted from markdown."""
    number: str       # e.g. "1.1"
    text: str         # question text
    section: str      # parent section name
    line_number: int  # source line for error reporting


@dataclass
class ParsedSection:
    """A section header extracted from markdown."""
    title: str
    description: str
    level: int        # 2 = section, 3 = subsection
    line_number: int


@dataclass
class ValidationIssue:
    """A validation finding."""
    severity: str     # ERROR, WARN, INFO
    message: str
    line_number: Optional[int] = None
    field: Optional[str] = None


# ── Markdown Parser ──

class MarkdownSurveyParser:
    """Parses a structured markdown survey into sections and questions."""

    # Match ## Section N: Title or ## Title
    SECTION_RE = re.compile(r'^##\s+(.+)$')
    SUBSECTION_RE = re.compile(r'^###\s+(.+)$')
    # Match **N.N** or **N.N.N** question text
    QUESTION_RE = re.compile(r'^\*\*(\d+(?:\.\d+)+)\*\*\s+(.+)$')
    # Match lines that are just --- (horizontal rules)
    HR_RE = re.compile(r'^-{3,}$')

    def __init__(self, content: str):
        self.lines = content.split('\n')
        self.sections: list[ParsedSection] = []
        self.questions: list[ParsedQuestion] = []
        self.preamble_lines: list[str] = []
        self.instruction_lines: list[str] = []
        self.current_section = ""
        self._parse()

    def _parse(self):
        in_preamble = True
        in_instructions = False
        current_description_lines = []
        pending_section = None
        i = 0

        while i < len(self.lines):
            line = self.lines[i].strip()
            i += 1

            # Skip horizontal rules
            if self.HR_RE.match(line):
                continue

            # Skip the title line (# Title)
            if line.startswith('# ') and not line.startswith('## '):
                in_preamble = True
                continue

            # Check for "How to Approach This" section
            if line.lower().startswith('## how to approach'):
                in_preamble = False
                in_instructions = True
                continue

            # Section header (##)
            section_match = self.SECTION_RE.match(line)
            if section_match and not line.startswith('###'):
                in_preamble = False
                in_instructions = False

                # Flush pending section description
                if pending_section:
                    pending_section.description = ' '.join(
                        current_description_lines).strip()
                    current_description_lines = []

                title = section_match.group(1).strip()
                self.current_section = title
                pending_section = ParsedSection(
                    title=title,
                    description="",
                    level=2,
                    line_number=i
                )
                self.sections.append(pending_section)
                continue

            # Subsection header (###)
            subsection_match = self.SUBSECTION_RE.match(line)
            if subsection_match:
                in_preamble = False
                in_instructions = False

                # Flush pending section description
                if pending_section:
                    pending_section.description = ' '.join(
                        current_description_lines).strip()
                    current_description_lines = []

                title = subsection_match.group(1).strip()
                pending_section = ParsedSection(
                    title=title,
                    description="",
                    level=3,
                    line_number=i
                )
                self.sections.append(pending_section)
                continue

            # Question line
            q_match = self.QUESTION_RE.match(line)
            if q_match:
                in_preamble = False
                in_instructions = False

                # Flush pending section description
                if pending_section:
                    pending_section.description = ' '.join(
                        current_description_lines).strip()
                    current_description_lines = []
                    pending_section = None

                self.questions.append(ParsedQuestion(
                    number=q_match.group(1),
                    text=q_match.group(2).strip(),
                    section=self.current_section,
                    line_number=i
                ))
                continue

            # Accumulate content
            if line:
                if in_preamble:
                    # Skip bold metadata lines like **Version:** etc.
                    if not line.startswith('**'):
                        self.preamble_lines.append(line)
                elif in_instructions:
                    self.instruction_lines.append(line)
                elif pending_section:
                    current_description_lines.append(line)

        # Flush final pending section
        if pending_section and current_description_lines:
            pending_section.description = ' '.join(
                current_description_lines).strip()


# ── Workspace Resolution ──

def _api_request(url: str, token: str, method: str = "GET",
                 data: Optional[dict] = None) -> dict:
    """Make an authenticated Typeform API request."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(
            f"Typeform API {method} {url} returned {e.code}: {error_body}"
        )


def list_workspaces(token: str) -> list[dict]:
    """Fetch all workspaces for the authenticated account."""
    all_items = []
    page = 1
    while True:
        result = _api_request(
            f"https://api.typeform.com/workspaces?page={page}&page_size=200",
            token
        )
        all_items.extend(result.get("items", []))
        if page >= result.get("page_count", 1):
            break
        page += 1
    return all_items


def resolve_workspace(name: str, token: str) -> Optional[str]:
    """Resolve a workspace name to its API href. Returns None if not found."""
    workspaces = list_workspaces(token)
    for ws in workspaces:
        if ws["name"].strip().lower() == name.strip().lower():
            return ws["self"]["href"]
    return None


def create_workspace(name: str, token: str) -> str:
    """Create a new workspace and return its API href."""
    result = _api_request(
        "https://api.typeform.com/workspaces",
        token,
        method="POST",
        data={"name": name}
    )
    href = result["self"]["href"]
    ws_id = result["id"]
    print(f"  Created workspace '{name}' (id: {ws_id})")
    return href


def resolve_or_create_workspace(config: 'SurveyConfig', token: str) -> str:
    """Resolve workspace_name to href. Create if missing and create_workspace=True.

    Returns the resolved workspace href. Raises if workspace not found and
    create_workspace is False.
    """
    name = config.workspace_name.strip()
    if not name:
        # No name provided — use the href from config directly
        if not config.workspace_href:
            raise ValueError("Neither workspace_name nor workspace_href is set in config")
        return config.workspace_href

    print(f"Resolving workspace '{name}'...")
    href = resolve_workspace(name, token)

    if href:
        print(f"  Found: {href}")
        return href

    if config.create_workspace:
        print(f"  Workspace '{name}' not found — creating it...")
        return create_workspace(name, token)

    raise ValueError(
        f"Workspace '{name}' not found. Set create_workspace=true in config "
        f"or use --create-workspace to create it automatically."
    )


# ── Markdown-to-Typeform Converter ──

def _ref():
    return str(uuid.uuid4())


def _convert_markdown_bold(text: str) -> str:
    """Convert markdown **bold** to Typeform *bold* syntax."""
    return re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)


def build_typeform_payload(
    parsed: MarkdownSurveyParser,
    config: SurveyConfig
) -> dict:
    """Build a complete Typeform API payload from parsed markdown and config."""

    fields = []

    # ── 1. Contact capture ──
    subfields = []
    field_map = {
        "first_name": ("First name", "short_text"),
        "last_name": ("Last name", "short_text"),
        "company": ("Company", "short_text"),
        "email": ("Email", "email"),
        "phone": ("Phone", "phone_number"),
    }

    for key in config.contact_fields:
        if key in field_map:
            label, ftype = field_map[key]
            subfields.append({
                "ref": _ref(),
                "title": label,
                "type": ftype,
                "subfield_key": key,
                "properties": {},
                "validations": {"required": True}
            })

    if subfields:
        fields.append({
            "ref": _ref(),
            "title": config.contact_prompt,
            "type": "contact_info",
            "properties": {
                "description": "All fields are required.",
                "fields": subfields
            },
            "validations": {"required": True}
        })

    # ── 2. Instructions screen ──
    instructions_text = config.instructions_text or '\n\n'.join(
        parsed.instruction_lines)
    if instructions_text:
        fields.append({
            "ref": _ref(),
            "title": config.instructions_title,
            "type": "statement",
            "properties": {
                "description": _convert_markdown_bold(instructions_text),
                "button_text": "Continue",
                "hide_marks": True
            }
        })

    # ── 3. Sections and questions ──
    for section in parsed.sections:
        # Skip subsections unless configured to keep them
        if section.level == 3 and not config.keep_subsections:
            continue

        fields.append({
            "ref": _ref(),
            "title": section.title,
            "type": "statement",
            "properties": {
                "description": _convert_markdown_bold(section.description),
                "button_text": "Continue",
                "hide_marks": True
            }
        })

    # Now add questions in order, grouped after their section
    # Rebuild: interleave sections and questions
    fields_ordered = []

    # Keep contact and instructions
    fields_ordered.extend(fields[:2] if len(fields) >= 2 else fields)

    # Build section→questions map
    section_questions = {}
    for q in parsed.questions:
        section_questions.setdefault(q.section, []).append(q)

    # Emit sections with their questions
    seen_sections = set()
    for section in parsed.sections:
        if section.level == 3 and not config.keep_subsections:
            continue

        fields_ordered.append({
            "ref": _ref(),
            "title": section.title,
            "type": "statement",
            "properties": {
                "description": _convert_markdown_bold(section.description),
                "button_text": "Continue",
                "hide_marks": True
            }
        })

        # Add questions for this section (only for level-2 sections)
        if section.level == 2 and section.title not in seen_sections:
            seen_sections.add(section.title)
            for q in section_questions.get(section.title, []):
                fields_ordered.append({
                    "ref": _ref(),
                    "title": f"*{q.number}* {_convert_markdown_bold(q.text)}",
                    "type": "long_text",
                    "properties": {},
                    "validations": {
                        "required": config.all_required
                    }
                })

    # ── 4. File upload (always last) ──
    fields_ordered.append({
        "ref": _ref(),
        "title": "Document Uploads",
        "type": "statement",
        "properties": {
            "description": ("If you have any supporting documents, please upload "
                          "them on the next screen. These are helpful, not required."),
            "button_text": "Continue",
            "hide_marks": True
        }
    })
    fields_ordered.append({
        "ref": _ref(),
        "title": "Upload any relevant documents here.",
        "type": "file_upload",
        "properties": {},
        "validations": {"required": False}
    })

    # ── Assemble payload ──
    welcome_desc = config.welcome_description or ' '.join(
        parsed.preamble_lines).strip()

    payload = {
        "title": config.title,
        "type": "quiz",
        "workspace": {"href": config.workspace_href},
        "theme": {"href": config.theme_href},
        "settings": {
            "language": "en",
            "progress_bar": "proportion",
            "show_progress_bar": True,
            "show_typeform_branding": config.show_typeform_branding,
            "show_question_number": True,
            "show_time_to_complete": True,
            "is_public": True,
            "hide_navigation": False,
            "free_form_navigation": False,
            "autosave_progress": config.autosave,
            "show_key_hint_on_choices": False,
            "show_number_of_submissions": False,
            "show_cookie_consent": False,
            "are_uploads_public": False,
            "meta": {
                "title": config.meta_title or f"{config.title} | SuccessCOACHING",
                "description": config.meta_description or welcome_desc[:160],
                "allow_indexing": False
            }
        },
        "welcome_screens": [{
            "ref": _ref(),
            "title": config.title,
            "properties": {
                "description": welcome_desc,
                "show_button": True,
                "button_text": config.welcome_button_text
            }
        }],
        "thankyou_screens": [
            {
                "ref": _ref(),
                "title": config.thankyou_title,
                "type": "thankyou_screen",
                "properties": {
                    "description": config.thankyou_description,
                    "show_button": bool(config.thankyou_redirect_url),
                    "button_text": config.thankyou_button_text or "Visit SuccessCOACHING",
                    "button_mode": "redirect" if config.thankyou_redirect_url else "default_redirect",
                    "redirect_url": config.thankyou_redirect_url or "https://successcoaching.co",
                    "share_icons": False
                }
            },
            {
                "ref": "default_tys",
                "title": "All done! Thanks for your time.",
                "type": "thankyou_screen",
                "properties": {"show_button": False, "share_icons": False}
            }
        ],
        "fields": fields_ordered
    }

    return payload


# ── Validator ──

def validate_payload(payload: dict, config: SurveyConfig) -> list[ValidationIssue]:
    """Validate a Typeform payload before pushing to the API."""
    issues = []

    fields = payload.get("fields", [])

    # ── Required config checks ──
    if not config.title:
        issues.append(ValidationIssue("ERROR", "Survey title is empty"))
    if not config.workspace_href:
        issues.append(ValidationIssue("ERROR", "Workspace href is missing"))
    if not config.theme_href:
        issues.append(ValidationIssue("ERROR", "Theme href is missing"))
    if not config.account_id:
        issues.append(ValidationIssue("ERROR", "Account ID is missing"))

    # ── Contact capture check ──
    contact_fields = [f for f in fields if f.get("type") == "contact_info"]
    if not contact_fields:
        issues.append(ValidationIssue("ERROR",
            "No contact_info field found — survey won't capture respondent identity"))
    elif fields[0].get("type") != "contact_info":
        issues.append(ValidationIssue("WARN",
            "Contact capture is not the first field — respondents should identify themselves first"))

    # ── Instructions check ──
    statement_fields = [f for f in fields if f.get("type") == "statement"]
    instructions_found = any("approach" in f.get("title", "").lower()
                           for f in statement_fields)
    if not instructions_found:
        issues.append(ValidationIssue("WARN",
            "No 'How to Approach This' instructions screen found"))

    # ── Markdown syntax check ──
    for i, f in enumerate(fields):
        title = f.get("title", "")
        desc = f.get("properties", {}).get("description", "")

        # Check for markdown **bold** that won't render in Typeform
        if "**" in title:
            issues.append(ValidationIssue("ERROR",
                f"Field {i}: Double-asterisk **bold** in title won't render. "
                f"Typeform uses single *bold*.",
                field=title[:60]))
        if "**" in desc:
            issues.append(ValidationIssue("WARN",
                f"Field {i}: Double-asterisk **bold** in description.",
                field=title[:60]))

        # Check for excessively long titles (Typeform renders poorly over ~300 chars)
        if len(title) > 300:
            issues.append(ValidationIssue("WARN",
                f"Field {i}: Title is {len(title)} chars — may render poorly. "
                f"Consider moving context to the description field.",
                field=title[:60]))

    # ── Question numbering continuity ──
    question_fields = [f for f in fields if f.get("type") == "long_text"]
    numbers = []
    for f in question_fields:
        match = re.match(r'^\*(\d+(?:\.\d+)+)\*', f.get("title", ""))
        if match:
            numbers.append(match.group(1))

    if numbers:
        # Check for gaps
        seen = set(numbers)
        for n in numbers:
            parts = n.split('.')
            if len(parts) == 2:
                section, q = int(parts[0]), int(parts[1])
                if q > 1:
                    prev = f"{section}.{q-1}"
                    if prev not in seen:
                        issues.append(ValidationIssue("WARN",
                            f"Question numbering gap: {prev} is missing before {n}"))

    # ── Required fields check ──
    non_required_questions = [f for f in question_fields
                            if not f.get("validations", {}).get("required", False)]
    if non_required_questions and config.all_required:
        issues.append(ValidationIssue("ERROR",
            f"{len(non_required_questions)} questions are not marked required "
            f"but config says all_required=True"))

    # ── Field count summary ──
    q_count = len(question_fields)
    s_count = len(statement_fields)
    total = len(fields)

    issues.append(ValidationIssue("INFO",
        f"Payload summary: {total} fields total — {q_count} questions, "
        f"{s_count} statement screens, "
        f"{total - q_count - s_count} other"))

    # Screen-to-question ratio
    if s_count > 0 and q_count / s_count < 3:
        issues.append(ValidationIssue("WARN",
            f"Low question-to-statement ratio ({q_count}:{s_count}). "
            f"Consider consolidating section dividers to reduce click fatigue."))

    return issues


def validate_config_file(config_path: str) -> tuple[SurveyConfig, list[ValidationIssue]]:
    """Load and validate a config file, returning config and any issues."""
    issues = []

    # workspace_href is only required if workspace_name is not set
    required_keys = ["title", "theme_href", "account_id"]

    try:
        with open(config_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        issues.append(ValidationIssue("ERROR", f"Config file not found: {config_path}"))
        return SurveyConfig(title="", workspace_href="", theme_href="", account_id=""), issues
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue("ERROR", f"Invalid JSON in config: {e}"))
        return SurveyConfig(title="", workspace_href="", theme_href="", account_id=""), issues

    for key in required_keys:
        if key not in data or not data[key]:
            issues.append(ValidationIssue("ERROR", f"Required config key missing: {key}"))

    # Workspace: need either workspace_name or workspace_href
    has_ws_name = data.get("workspace_name", "").strip()
    has_ws_href = data.get("workspace_href", "").strip()
    if not has_ws_name and not has_ws_href:
        issues.append(ValidationIssue("ERROR",
            "Neither workspace_name nor workspace_href is set — "
            "one is required to target a workspace"))

    config = SurveyConfig(**{k: v for k, v in data.items()
                           if k in SurveyConfig.__dataclass_fields__})
    return config, issues


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(
        description="Convert a markdown survey to a Typeform API payload")
    parser.add_argument("markdown", nargs="?", default=None,
                       help="Path to the markdown survey file")
    parser.add_argument("--config",
                       help="Path to the JSON config file")
    parser.add_argument("--output", default="typeform_payload.json",
                       help="Output JSON file path")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate, don't produce output")
    parser.add_argument("--keep-subsections", action="store_true",
                       help="Keep ### subsection dividers as statement screens")
    # Workspace targeting
    parser.add_argument("--workspace", metavar="NAME",
                       help="Target workspace by name (overrides config workspace_name)")
    parser.add_argument("--create-workspace", action="store_true",
                       help="Create the workspace if it doesn't exist")
    # API token (required for workspace resolution; can also use TYPEFORM_TOKEN env var)
    parser.add_argument("--token", metavar="TOKEN",
                       help="Typeform personal access token (or set TYPEFORM_TOKEN env var)")
    # Direct push mode
    parser.add_argument("--push", action="store_true",
                       help="After building payload, push directly to Typeform API")
    parser.add_argument("--form-id", metavar="ID",
                       help="Form ID to update (overrides config form_id)")
    # List workspaces utility
    parser.add_argument("--list-workspaces", action="store_true",
                       help="List all workspaces and exit")
    args = parser.parse_args()

    # Resolve token from flag, env, or fail
    import os
    token = args.token or os.environ.get("TYPEFORM_TOKEN", "")

    # ── List workspaces mode ──
    if args.list_workspaces:
        if not token:
            print("❌ --token or TYPEFORM_TOKEN env var required for --list-workspaces")
            sys.exit(1)
        workspaces = list_workspaces(token)
        print(f"{'Name':<45} {'ID':<10} {'Forms':>5}")
        print("-" * 65)
        for ws in sorted(workspaces, key=lambda w: w["name"].lower()):
            name = ws["name"]
            ws_id = ws["id"]
            form_count = ws.get("forms", {}).get("count", "?")
            print(f"{name:<45} {ws_id:<10} {form_count:>5}")
        print(f"\n{len(workspaces)} workspaces total")
        sys.exit(0)

    # ── Require markdown and config for normal mode ──
    if not args.markdown:
        parser.error("the following arguments are required: markdown")
    if not args.config:
        parser.error("the following arguments are required: --config")

    # Load config
    config, config_issues = validate_config_file(args.config)
    if args.keep_subsections:
        config.keep_subsections = True

    # CLI overrides for workspace
    if args.workspace:
        config.workspace_name = args.workspace
    if args.create_workspace:
        config.create_workspace = True
    if args.form_id:
        config.form_id = args.form_id

    # ── Resolve workspace if workspace_name is set ──
    needs_workspace_resolution = bool(config.workspace_name.strip())
    if needs_workspace_resolution:
        if not token:
            print("❌ --token or TYPEFORM_TOKEN env var required for workspace resolution")
            sys.exit(1)
        try:
            config.workspace_href = resolve_or_create_workspace(config, token)
        except ValueError as e:
            config_issues.append(ValidationIssue("ERROR", str(e)))

    # Parse markdown
    md_content = Path(args.markdown).read_text()
    parsed = MarkdownSurveyParser(md_content)

    print(f"Parsed: {len(parsed.sections)} sections, {len(parsed.questions)} questions")
    print(f"  Preamble: {len(parsed.preamble_lines)} lines")
    print(f"  Instructions: {len(parsed.instruction_lines)} lines")

    # Build payload
    payload = build_typeform_payload(parsed, config)

    # Validate
    all_issues = config_issues + validate_payload(payload, config)

    # Report
    errors = [i for i in all_issues if i.severity == "ERROR"]
    warns = [i for i in all_issues if i.severity == "WARN"]
    infos = [i for i in all_issues if i.severity == "INFO"]

    print(f"\nValidation: {len(errors)} errors, {len(warns)} warnings, {len(infos)} info")
    for issue in all_issues:
        icon = {"ERROR": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ "}[issue.severity]
        print(f"  {icon} [{issue.severity}] {issue.message}")
        if issue.field:
            print(f"     └─ {issue.field}...")

    if errors and not args.validate_only:
        print(f"\n❌ {len(errors)} error(s) found. Fix before pushing to Typeform.")
        sys.exit(1)

    if args.validate_only:
        sys.exit(0 if not errors else 1)

    # Write output
    with open(args.output, 'w') as f:
        json.dump(payload, f, indent=2)

    fields = payload.get("fields", [])
    q_count = sum(1 for f in fields if f["type"] == "long_text")
    print(f"\n✅ Payload written to {args.output}")
    print(f"   {len(fields)} fields, {q_count} questions")
    print(f"   Workspace: {config.workspace_href}")
    if config.form_id:
        print(f"   Ready to PUT https://api.typeform.com/forms/{config.form_id}")

    # ── Direct push mode ──
    if args.push:
        form_id = config.form_id
        if not form_id:
            print("\n❌ --push requires --form-id or form_id in config")
            sys.exit(1)
        if not token:
            print("\n❌ --push requires --token or TYPEFORM_TOKEN env var")
            sys.exit(1)

        print(f"\nPushing to form {form_id}...")
        try:
            result = _api_request(
                f"https://api.typeform.com/forms/{form_id}",
                token,
                method="PUT",
                data=payload
            )
            result_fields = len(result.get("fields", []))
            display_url = result.get("_links", {}).get("display", "")
            print(f"✅ Push successful: {result_fields} fields")
            if display_url:
                print(f"   URL: {display_url}")
        except RuntimeError as e:
            print(f"\n❌ Push failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
