#!/usr/bin/env python3
"""
Typeform Response Analyzer

Pulls responses from the Typeform Responses API, structures them by
section and question, computes completion analytics, and outputs a
structured markdown report ready for analysis.

Usage:
    # Pull and analyze all completed responses
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN

    # Pull only responses since a date
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --since 2026-01-01

    # Include partial/started responses
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --include-partial

    # Output raw structured JSON instead of markdown report
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --json

    # Export responses as CSV (one row per respondent, one column per question)
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --csv

    # Check platform status before pulling
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --check-status

    # Limit to N most recent responses
    python typeform_responses.py <FORM_ID> --token $TYPEFORM_TOKEN --limit 50
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

API_BASE = "https://api.typeform.com"
PAGE_SIZE = 1000  # Max per the API


# ─── Data Models ────────────────────────────────────────────────────────


@dataclass
class FormField:
    """A field from the form definition."""
    id: str
    ref: str
    title: str
    type: str
    properties: dict = field(default_factory=dict)

    @property
    def is_question(self) -> bool:
        return self.type not in ("statement", "contact_info")

    @property
    def section_number(self) -> str | None:
        """Extract section number like '1.1' from title '*1.1* ...'."""
        m = re.match(r"\*(\d+\.\d+)\*", self.title)
        return m.group(1) if m else None

    @property
    def clean_title(self) -> str:
        """Title without the bold number prefix."""
        return re.sub(r"^\*\d+\.\d+\*\s*", "", self.title)


@dataclass
class Answer:
    """A single answer from a response."""
    field_id: str
    field_ref: str
    field_type: str
    answer_type: str
    value: Any

    @property
    def text_value(self) -> str:
        """Normalize answer to string for reporting."""
        if self.answer_type == "text":
            return str(self.value)
        elif self.answer_type == "email":
            return str(self.value)
        elif self.answer_type == "number":
            return str(self.value)
        elif self.answer_type == "boolean":
            return "Yes" if self.value else "No"
        elif self.answer_type == "date":
            return str(self.value)
        elif self.answer_type == "choice":
            if isinstance(self.value, dict):
                return self.value.get("label", str(self.value))
            return str(self.value)
        elif self.answer_type == "choices":
            if isinstance(self.value, dict):
                return ", ".join(self.value.get("labels", []))
            return str(self.value)
        elif self.answer_type == "file_url":
            return str(self.value)
        elif self.answer_type == "url":
            return str(self.value)
        return str(self.value)


@dataclass
class Response:
    """A single form response."""
    response_id: str
    submitted_at: str | None
    landed_at: str | None
    answers: list[Answer]
    hidden: dict = field(default_factory=dict)
    variables: list[dict] = field(default_factory=list)
    calculated_score: int | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.submitted_at is not None


@dataclass
class FormDefinition:
    """Form structure — fields, sections, screens."""
    form_id: str
    title: str
    fields: list[FormField]
    welcome_screens: list[dict] = field(default_factory=list)
    thankyou_screens: list[dict] = field(default_factory=list)

    @property
    def question_fields(self) -> list[FormField]:
        return [f for f in self.fields if f.is_question]

    @property
    def sections(self) -> list[FormField]:
        return [f for f in self.fields if f.type == "statement"]


# ─── API Client ─────────────────────────────────────────────────────────


def api_get(path: str, token: str, params: dict | None = None) -> dict:
    """Make a GET request to the Typeform API."""
    url = f"{API_BASE}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if query:
            url = f"{url}?{query}"

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"❌ API error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ Connection error: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_form_definition(form_id: str, token: str) -> FormDefinition:
    """Get the form definition (structure, fields, screens)."""
    data = api_get(f"/forms/{form_id}", token)

    fields = []
    for f in data.get("fields", []):
        fields.append(FormField(
            id=f["id"],
            ref=f.get("ref", ""),
            title=f.get("title", ""),
            type=f["type"],
            properties=f.get("properties", {}),
        ))

    return FormDefinition(
        form_id=form_id,
        title=data.get("title", ""),
        fields=fields,
        welcome_screens=data.get("welcome_screens", []),
        thankyou_screens=data.get("thankyou_screens", []),
    )


def fetch_responses(
    form_id: str,
    token: str,
    since: str | None = None,
    until: str | None = None,
    include_partial: bool = False,
    limit: int | None = None,
) -> list[Response]:
    """Fetch all responses with pagination."""
    all_responses: list[Response] = []
    after_token = None

    response_type = "completed,partial,started" if include_partial else "completed"

    while True:
        params = {
            "page_size": min(PAGE_SIZE, limit - len(all_responses)) if limit else PAGE_SIZE,
            "response_type": response_type,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if after_token:
            params["after"] = after_token

        data = api_get(f"/forms/{form_id}/responses", token, params)
        items = data.get("items", [])

        if not items:
            break

        for item in items:
            answers = []
            for a in item.get("answers", []):
                fld = a.get("field", {})
                atype = a.get("type", "text")

                # Extract value based on answer type
                value = a.get(atype, a.get("text", ""))

                answers.append(Answer(
                    field_id=fld.get("id", ""),
                    field_ref=fld.get("ref", ""),
                    field_type=fld.get("type", ""),
                    answer_type=atype,
                    value=value,
                ))

            calc = item.get("calculated", {})
            all_responses.append(Response(
                response_id=item.get("response_id", item.get("token", "")),
                submitted_at=item.get("submitted_at"),
                landed_at=item.get("landed_at"),
                answers=answers,
                hidden=item.get("hidden", {}),
                variables=item.get("variables", []),
                calculated_score=calc.get("score") if calc else None,
                metadata=item.get("metadata", {}),
            ))

        # Check if we've hit the limit
        if limit and len(all_responses) >= limit:
            all_responses = all_responses[:limit]
            break

        # Cursor pagination — use the last item's token
        total = data.get("total_items", 0)
        if len(all_responses) >= total:
            break

        # Use the last response token as cursor
        last_token = items[-1].get("token", items[-1].get("response_id"))
        if last_token and last_token != after_token:
            after_token = last_token
        else:
            break

    return all_responses


# ─── Analysis ────────────────────────────────────────────────────────────


def build_question_map(form: FormDefinition) -> dict[str, FormField]:
    """Map field IDs and refs to FormField objects."""
    by_id = {f.id: f for f in form.fields}
    by_ref = {f.ref: f for f in form.fields if f.ref}
    return {**by_id, **by_ref}


def compute_analytics(
    form: FormDefinition, responses: list[Response]
) -> dict[str, Any]:
    """Compute response analytics."""
    qmap = build_question_map(form)
    questions = form.question_fields

    total = len(responses)
    completed = sum(1 for r in responses if r.is_complete)

    # Per-question answer collection
    question_answers: dict[str, list[str]] = defaultdict(list)
    question_response_count: dict[str, int] = defaultdict(int)

    for resp in responses:
        answered_fields = set()
        for ans in resp.answers:
            fld = qmap.get(ans.field_id) or qmap.get(ans.field_ref)
            if fld and fld.is_question:
                text = ans.text_value.strip()
                if text:
                    question_answers[fld.id].append(text)
                    answered_fields.add(fld.id)

        for fid in answered_fields:
            question_response_count[fid] += 1

    # Submission timeline
    timestamps = []
    for r in responses:
        ts = r.submitted_at or r.landed_at
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
            except (ValueError, TypeError):
                pass

    timeline = {}
    if timestamps:
        timestamps.sort()
        timeline["first"] = timestamps[0].isoformat()
        timeline["last"] = timestamps[-1].isoformat()
        if len(timestamps) > 1:
            span = (timestamps[-1] - timestamps[0]).total_seconds()
            timeline["span_days"] = round(span / 86400, 1)

    # Per-question stats
    question_stats = []
    for q in questions:
        answers = question_answers.get(q.id, [])
        resp_count = question_response_count.get(q.id, 0)

        stat = {
            "field_id": q.id,
            "ref": q.ref,
            "title": q.title,
            "clean_title": q.clean_title,
            "section_number": q.section_number,
            "type": q.type,
            "response_count": resp_count,
            "response_rate": round(resp_count / total * 100, 1) if total else 0,
            "answers": answers,
        }

        # Word count stats for text answers
        if q.type in ("long_text", "short_text") and answers:
            word_counts = [len(a.split()) for a in answers]
            stat["avg_word_count"] = round(sum(word_counts) / len(word_counts), 1)
            stat["min_word_count"] = min(word_counts)
            stat["max_word_count"] = max(word_counts)

        # For choice/rating fields, compute distribution
        if q.type in ("multiple_choice", "rating", "opinion_scale", "nps", "yes_no", "dropdown"):
            dist: dict[str, int] = defaultdict(int)
            for a in answers:
                dist[a] += 1
            stat["distribution"] = dict(sorted(dist.items(), key=lambda x: -x[1]))

        question_stats.append(stat)

    # Section grouping
    sections = []
    current_section = None
    current_questions = []

    for fld in form.fields:
        if fld.type == "statement" and fld.title.startswith("Section"):
            if current_section is not None:
                sections.append({
                    "title": current_section.title,
                    "questions": current_questions,
                })
            current_section = fld
            current_questions = []
        elif fld.is_question:
            qstat = next((s for s in question_stats if s["field_id"] == fld.id), None)
            if qstat:
                current_questions.append(qstat)

    if current_section is not None:
        sections.append({
            "title": current_section.title,
            "questions": current_questions,
        })

    # Catch questions not in any section
    sectioned_ids = {q["field_id"] for s in sections for q in s["questions"]}
    unsectioned = [q for q in question_stats if q["field_id"] not in sectioned_ids]
    if unsectioned:
        sections.insert(0, {"title": "General", "questions": unsectioned})

    return {
        "form_id": form.form_id,
        "form_title": form.title,
        "total_responses": total,
        "completed_responses": completed,
        "completion_rate": round(completed / total * 100, 1) if total else 0,
        "timeline": timeline,
        "sections": sections,
        "question_stats": question_stats,
    }


# ─── Output Formatters ──────────────────────────────────────────────────


def format_markdown_report(analytics: dict) -> str:
    """Generate a structured markdown analysis report."""
    lines = []
    a = analytics

    lines.append(f"# Response Analysis: {a['form_title']}")
    lines.append("")
    lines.append(f"**Form ID:** `{a['form_id']}`")
    lines.append(f"**Total Responses:** {a['total_responses']} ({a['completed_responses']} completed, {a['total_responses'] - a['completed_responses']} partial)")
    lines.append(f"**Completion Rate:** {a['completion_rate']}%")

    tl = a.get("timeline", {})
    if tl:
        if "first" in tl:
            lines.append(f"**Collection Period:** {tl.get('first', '?')[:10]} to {tl.get('last', '?')[:10]} ({tl.get('span_days', '?')} days)")
    lines.append("")

    # Per-section analysis
    for section in a["sections"]:
        lines.append(f"---")
        lines.append("")
        lines.append(f"## {section['title']}")
        lines.append("")

        for q in section["questions"]:
            num = q.get("section_number", "")
            title_display = f"**{num}** {q['clean_title']}" if num else f"**{q['clean_title']}**"
            lines.append(f"### {title_display}")
            lines.append("")
            lines.append(f"*Responses: {q['response_count']}/{a['total_responses']} ({q['response_rate']}%) · Type: {q['type']}*")
            lines.append("")

            # Distribution for structured fields
            if "distribution" in q:
                for val, count in q["distribution"].items():
                    pct = round(count / q["response_count"] * 100, 1) if q["response_count"] else 0
                    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                    lines.append(f"  {bar} {val}: {count} ({pct}%)")
                lines.append("")

            # Word count stats for text fields
            if "avg_word_count" in q:
                lines.append(f"*Average length: {q['avg_word_count']} words (range: {q['min_word_count']}–{q['max_word_count']})*")
                lines.append("")

            # Individual answers
            answers = q.get("answers", [])
            if answers:
                if q["type"] in ("long_text", "short_text"):
                    for i, ans in enumerate(answers, 1):
                        # Truncate very long answers for the report
                        display = ans if len(ans) <= 500 else ans[:497] + "..."
                        lines.append(f"**R{i}:** {display}")
                        lines.append("")
                elif q["type"] == "file_upload":
                    for i, ans in enumerate(answers, 1):
                        lines.append(f"- R{i}: [uploaded file]({ans})")
                    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by typeform-response-analyzer*")

    return "\n".join(lines)


def format_csv(analytics: dict) -> str:
    """Generate CSV with one row per respondent, one column per question."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Build header from question stats
    questions = analytics.get("question_stats", [])
    header = ["response_number"]
    field_order = []
    for q in questions:
        num = q.get("section_number", "")
        label = f"{num} {q['clean_title']}" if num else q["clean_title"]
        # Truncate header to 80 chars
        header.append(label[:80])
        field_order.append(q["field_id"])

    writer.writerow(header)

    # Reconstruct per-respondent rows from the analytics answers
    # The answers list in each question_stat is ordered by respondent
    total = analytics["total_responses"]
    for i in range(total):
        row = [i + 1]
        for q in questions:
            answers = q.get("answers", [])
            row.append(answers[i] if i < len(answers) else "")
        writer.writerow(row)

    return output.getvalue()


# ─── Status Check Integration ───────────────────────────────────────────


def check_typeform_status() -> bool:
    """Quick status check. Returns True if APIs are operational."""
    try:
        req = urllib.request.Request(
            "https://status.typeform.com/api/v2/status.json",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            indicator = data.get("status", {}).get("indicator", "unknown")
            desc = data.get("status", {}).get("description", "Unknown")

            if indicator == "none":
                print(f"✅ Typeform: {desc}", file=sys.stderr)
                return True
            else:
                print(f"⚠️  Typeform: {desc}", file=sys.stderr)
                print("   Consider checking https://status.typeform.com before proceeding", file=sys.stderr)
                return True  # Don't block — warn only
    except Exception:
        print("⚠️  Could not check status.typeform.com — proceeding anyway", file=sys.stderr)
        return True


# ─── CLI ─────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Pull and analyze Typeform survey responses"
    )
    parser.add_argument("form_id", help="Typeform form ID")
    parser.add_argument(
        "--token",
        default=os.environ.get("TYPEFORM_TOKEN"),
        help="Typeform personal access token (or set TYPEFORM_TOKEN env var)",
    )
    parser.add_argument("--since", help="ISO 8601 date — only responses after this date")
    parser.add_argument("--until", help="ISO 8601 date — only responses before this date")
    parser.add_argument("--include-partial", action="store_true", help="Include partial/started responses")
    parser.add_argument("--limit", type=int, help="Maximum number of responses to pull")
    parser.add_argument("--json", action="store_true", help="Output raw structured JSON")
    parser.add_argument("--csv", action="store_true", help="Output CSV (one row per respondent)")
    parser.add_argument("--output", "-o", help="Write report to file instead of stdout")
    parser.add_argument("--check-status", action="store_true", help="Check status.typeform.com first")
    parser.add_argument(
        "--form-only",
        action="store_true",
        help="Print form structure only (no responses)",
    )

    args = parser.parse_args()

    if not args.token:
        print("❌ No token provided. Use --token or set TYPEFORM_TOKEN env var.", file=sys.stderr)
        sys.exit(1)

    # Optional status check
    if args.check_status:
        check_typeform_status()

    # Fetch form definition
    print(f"Fetching form definition for {args.form_id}...", file=sys.stderr)
    form = fetch_form_definition(args.form_id, args.token)
    print(f"  Title: {form.title}", file=sys.stderr)
    print(f"  Fields: {len(form.fields)} ({len(form.question_fields)} questions)", file=sys.stderr)

    if args.form_only:
        for i, f in enumerate(form.fields):
            marker = "Q" if f.is_question else "S" if f.type == "statement" else " "
            print(f"  [{marker}] {f.type:15s} | {f.title[:70]}")
        return

    # Fetch responses
    print(f"Fetching responses...", file=sys.stderr)
    responses = fetch_responses(
        form_id=args.form_id,
        token=args.token,
        since=args.since,
        until=args.until,
        include_partial=args.include_partial,
        limit=args.limit,
    )
    print(f"  Retrieved: {len(responses)} responses", file=sys.stderr)

    if not responses:
        print("No responses found.", file=sys.stderr)
        return

    # Analyze
    analytics = compute_analytics(form, responses)

    # Output
    if args.json:
        # Strip raw answers from JSON to keep it manageable
        output = json.dumps(analytics, indent=2, default=str)
    elif args.csv:
        output = format_csv(analytics)
    else:
        output = format_markdown_report(analytics)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"✅ Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
