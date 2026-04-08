#!/usr/bin/env python3
"""
Typeform Platform Status Checker

Checks https://status.typeform.com for current system status.
Reports overall health plus component-level details for the services
that matter to the MCP+ toolkit: Create API, Responses API, Webhooks API,
form rendering, and submission handling.

Usage:
    python typeform_status.py                  # Quick summary
    python typeform_status.py --all            # All components
    python typeform_status.py --json           # Raw JSON output
    python typeform_status.py --api-only       # Developer Platform components only
    python typeform_status.py --check          # Exit code 0 if healthy, 1 if degraded
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any

STATUS_URL = "https://status.typeform.com/api/v2/status.json"
COMPONENTS_URL = "https://status.typeform.com/api/v2/components.json"
INCIDENTS_URL = "https://status.typeform.com/api/v2/incidents/unresolved.json"

# Components that directly affect MCP+ toolkit operations
CRITICAL_COMPONENT_NAMES = {
    "Create API",
    "Responses API",
    "Webhooks API",
    "Developer Portal",
    "Submit responses",
    "Open/Load forms",
    "Form creation",
    "Publish form",
}

# Group names (parent components with group_id=null)
GROUP_NAMES = {
    "Forms / Renderer",
    "Builder / Create UI",
    "Connect/Integrations",
    "Results",
    "Share Panel",
    "Workspaces, Teams & Templates",
    "Public Pages",
    "Developer Platform",
    "Admin",
    "Back-End",
}

STATUS_SYMBOLS = {
    "operational": "✅",
    "degraded_performance": "⚠️",
    "partial_outage": "🟠",
    "major_outage": "🔴",
    "under_maintenance": "🔧",
}

STATUS_LABELS = {
    "operational": "Operational",
    "degraded_performance": "Degraded",
    "partial_outage": "Partial Outage",
    "major_outage": "Major Outage",
    "under_maintenance": "Maintenance",
}


def fetch_json(url: str) -> dict[str, Any]:
    """Fetch JSON from a URL. Raises on failure."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ Could not reach status.typeform.com: {e}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError:
        print("❌ Invalid JSON from status.typeform.com", file=sys.stderr)
        sys.exit(2)


def fetch_status() -> dict[str, Any]:
    """Get overall status."""
    return fetch_json(STATUS_URL)


def fetch_components() -> list[dict[str, Any]]:
    """Get all components with their statuses."""
    data = fetch_json(COMPONENTS_URL)
    return data.get("components", [])


def fetch_incidents() -> list[dict[str, Any]]:
    """Get unresolved incidents."""
    data = fetch_json(INCIDENTS_URL)
    return data.get("incidents", [])


def format_status_line(name: str, status: str, indent: int = 0) -> str:
    """Format a single component status line."""
    symbol = STATUS_SYMBOLS.get(status, "❓")
    label = STATUS_LABELS.get(status, status)
    prefix = "  " * indent
    return f"{prefix}{symbol} {name}: {label}"


def build_component_tree(components: list[dict]) -> dict:
    """Organize components into groups → children."""
    groups = {}
    children = {}

    for c in components:
        cid = c["id"]
        gid = c.get("group_id")

        if gid is None:
            # This is a top-level group
            groups[cid] = c
            if cid not in children:
                children[cid] = []
        else:
            if gid not in children:
                children[gid] = []
            children[gid].append(c)

    return groups, children


def print_summary(status_data: dict, components: list[dict], incidents: list[dict]) -> bool:
    """Print a summary focused on MCP+ relevant services. Returns True if all healthy."""
    indicator = status_data.get("status", {}).get("indicator", "unknown")
    description = status_data.get("status", {}).get("description", "Unknown")
    updated = status_data.get("page", {}).get("updated_at", "")

    all_healthy = indicator == "none"

    # Header
    symbol = "✅" if all_healthy else STATUS_SYMBOLS.get(indicator, "❓")
    print(f"\n{symbol} Typeform Status: {description}")

    if updated:
        try:
            dt = datetime.fromisoformat(updated)
            now = datetime.now(timezone.utc)
            age = now - dt.astimezone(timezone.utc)
            mins = int(age.total_seconds() / 60)
            if mins < 2:
                age_str = "just now"
            elif mins < 60:
                age_str = f"{mins}m ago"
            else:
                age_str = f"{mins // 60}h {mins % 60}m ago"
            print(f"   Last updated: {age_str}")
        except (ValueError, TypeError):
            pass

    # Critical components for MCP+ operations
    critical = [c for c in components if c["name"] in CRITICAL_COMPONENT_NAMES]
    non_operational = [c for c in critical if c["status"] != "operational"]

    print(f"\n{'─' * 45}")
    print("MCP+ Critical Services:")

    if not non_operational:
        print("  ✅ All 8 critical services operational")
    else:
        for c in critical:
            if c["status"] != "operational":
                print(format_status_line(c["name"], c["status"], indent=1))
                all_healthy = False

    # Unresolved incidents
    if incidents:
        print(f"\n{'─' * 45}")
        print(f"⚠️  Active Incidents ({len(incidents)}):")
        for inc in incidents:
            name = inc.get("name", "Unknown")
            impact = inc.get("impact", "none")
            print(f"  • {name} (impact: {impact})")
            updates = inc.get("incident_updates", [])
            if updates:
                latest = updates[0]
                body = latest.get("body", "")
                if body:
                    # Truncate long updates
                    if len(body) > 120:
                        body = body[:117] + "..."
                    print(f"    └─ {body}")

    print()
    return all_healthy


def print_all_components(components: list[dict]) -> None:
    """Print every component grouped by parent."""
    groups, children_map = build_component_tree(components)

    print(f"\n{'─' * 50}")
    print("All Typeform Components:")
    print(f"{'─' * 50}")

    for gid, group in sorted(groups.items(), key=lambda x: x[1]["name"]):
        print(format_status_line(group["name"], group["status"]))
        for child in sorted(children_map.get(gid, []), key=lambda x: x["name"]):
            marker = "●" if child["name"] in CRITICAL_COMPONENT_NAMES else "○"
            symbol = STATUS_SYMBOLS.get(child["status"], "❓")
            label = STATUS_LABELS.get(child["status"], child["status"])
            print(f"    {marker} {symbol} {child['name']}: {label}")

    print(f"\n● = MCP+ critical service   ○ = other\n")


def print_api_only(components: list[dict]) -> None:
    """Print only Developer Platform components."""
    dev_group_id = None
    for c in components:
        if c["name"] == "Developer Platform" and c.get("group_id") is None:
            dev_group_id = c["id"]
            break

    if not dev_group_id:
        print("Developer Platform group not found")
        return

    print(f"\n{'─' * 40}")
    print("Developer Platform:")
    print(f"{'─' * 40}")

    api_components = [c for c in components if c.get("group_id") == dev_group_id]
    for c in sorted(api_components, key=lambda x: x["name"]):
        print(format_status_line(c["name"], c["status"], indent=1))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Check Typeform platform status (status.typeform.com)"
    )
    parser.add_argument("--all", action="store_true", help="Show all components")
    parser.add_argument("--api-only", action="store_true", help="Show Developer Platform only")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if healthy, 1 if degraded (for scripting)",
    )
    args = parser.parse_args()

    if args.json:
        status = fetch_status()
        components = fetch_components()
        incidents = fetch_incidents()
        print(json.dumps({
            "status": status,
            "components": components,
            "incidents": incidents,
        }, indent=2))
        return

    status = fetch_status()
    components = fetch_components()
    incidents = fetch_incidents()

    if args.api_only:
        print_api_only(components)
        return

    all_healthy = print_summary(status, components, incidents)

    if args.all:
        print_all_components(components)

    if args.check:
        sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
