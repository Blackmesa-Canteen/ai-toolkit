#!/usr/bin/env python3
"""
hierarchy.py — Domain and category hierarchy management for Trilium Notes.

Imports from client.py. Used by commands.py.
"""

import sys
from datetime import date

from client import (
    api_request,
    add_label,
    find_note_by_title,
    save_config,
    search_notes,
)


def _resolve_domain(config: dict, domain_arg: str | None) -> str:
    """Resolve which domain to use.

    - If domain_arg is provided, use it (error if not found).
    - If only one domain exists, auto-select it.
    - If multiple domains and no arg, error with list.
    """
    domains = config.get("domains", {})
    if not domains:
        print("ERROR: No domains configured. Run 'create-domain' first.", file=sys.stderr)
        sys.exit(1)

    if domain_arg:
        if domain_arg not in domains:
            print(f"ERROR: Domain '{domain_arg}' not found. Available: {', '.join(domains.keys())}", file=sys.stderr)
            sys.exit(1)
        return domain_arg

    if len(domains) == 1:
        return next(iter(domains))

    print(f"ERROR: Multiple domains configured. Use --domain to specify one: {', '.join(domains.keys())}", file=sys.stderr)
    sys.exit(1)


def get_or_create_domain_root(config: dict, config_path: str, domain_key: str) -> str:
    """Find or create a domain's root note (direct child of Trilium root)."""
    domains = config.get("domains", {})
    domain = domains.get(domain_key, {})

    root_id = domain.get("noteId")
    title = domain.get("title", domain_key.replace("_", " ").title())
    icon = domain.get("icon", "bx bx-note")
    description = domain.get("description", "")

    # Check cached noteId
    if root_id and root_id != "auto":
        try:
            resp = api_request(config, "GET", f"/notes/{root_id}")
            if isinstance(resp, dict) and resp.get("noteId"):
                return root_id
        except SystemExit:
            pass  # Note gone, recreate

    # Search for it
    existing = find_note_by_title(config, title)
    if existing:
        domain["noteId"] = existing
        config["domains"][domain_key] = domain
        save_config(config_path, config)
        return existing

    # Create it under Trilium root
    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": "root",
            "title": title,
            "type": "text",
            "content": f"<p>{description}</p>" if description else "<p></p>",
        },
    )
    root_id = resp.get("note", {}).get("noteId", "")
    if root_id:
        add_label(config, root_id, "iconClass", icon)
        domain["noteId"] = root_id
        config["domains"][domain_key] = domain
        save_config(config_path, config)
    return root_id


def ensure_category(config: dict, config_path: str, domain_key: str, category: str) -> str:
    """Find or create a category note under a domain root. Returns the category noteId."""
    domains = config.get("domains", {})
    domain = domains.get(domain_key, {})
    categories = domain.get("categories", {})

    if category not in categories:
        print(f"ERROR: Unknown category '{category}' in domain '{domain_key}'. Run 'list-categories --domain {domain_key}' to see valid categories, or 'create-category' to add one.", file=sys.stderr)
        sys.exit(1)

    cat_entry = categories[category]
    cached_id = cat_entry.get("noteId") if isinstance(cat_entry, dict) else cat_entry
    if cached_id and cached_id != "auto":
        try:
            resp = api_request(config, "GET", f"/notes/{cached_id}")
            if isinstance(resp, dict) and resp.get("noteId"):
                return cached_id
        except SystemExit:
            pass

    # Get domain root first
    root_id = get_or_create_domain_root(config, config_path, domain_key)

    # Read metadata from config entry
    cat_title = cat_entry.get("title", category.replace("_", " ").title()) if isinstance(cat_entry, dict) else category.replace("_", " ").title()
    cat_icon = cat_entry.get("icon", "bx bx-note") if isinstance(cat_entry, dict) else "bx bx-note"
    cat_desc = cat_entry.get("description", "") if isinstance(cat_entry, dict) else ""

    # Search for existing category
    existing = find_note_by_title(config, cat_title, parent_id=root_id)
    if existing:
        categories[category] = {
            "noteId": existing,
            "title": cat_title,
            "icon": cat_icon,
            "description": cat_desc,
        }
        domain["categories"] = categories
        config["domains"][domain_key] = domain
        save_config(config_path, config)
        return existing

    # Create category
    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": root_id,
            "title": cat_title,
            "type": "text",
            "content": f"<p>{cat_desc}</p>" if cat_desc else "<p></p>",
        },
    )
    cat_id = resp.get("note", {}).get("noteId", "")
    if cat_id:
        add_label(config, cat_id, "iconClass", cat_icon)
        categories[category] = {
            "noteId": cat_id,
            "title": cat_title,
            "icon": cat_icon,
            "description": cat_desc,
        }
        domain["categories"] = categories
        config["domains"][domain_key] = domain
        save_config(config_path, config)
    return cat_id


def get_day_note(config: dict, day: str | None = None) -> str:
    """Get today's day note via calendar API. Creates it if it doesn't exist."""
    if not day:
        day = date.today().isoformat()
    resp = api_request(config, "GET", f"/calendar/days/{day}")
    if isinstance(resp, dict):
        return resp.get("noteId", "")
    return ""


def find_related_notes(config: dict, topics: list[str], exclude_id: str = "") -> list[dict]:
    """Find notes that share topic labels, for creating relations."""
    related = []
    seen_ids = set()
    for topic in topics:
        results = search_notes(config, f"#topic={topic}")
        for note in results:
            nid = note.get("noteId", "")
            if nid and nid != exclude_id and nid not in seen_ids:
                seen_ids.add(nid)
                related.append(note)
                if len(related) >= 5:
                    return related
    return related


# --- Legacy: find or create AI Inbox ---


def find_or_create_inbox(config: dict) -> str:
    result = search_notes(config, "AI Inbox")
    for note in result:
        if note.get("title") == "AI Inbox":
            return note["noteId"]

    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": "root",
            "title": "AI Inbox",
            "type": "text",
            "content": "<p>Notes pushed by AI agents via ETAPI. Organized by date and topic.</p>",
        },
    )
    return resp.get("note", {}).get("noteId", "root")
