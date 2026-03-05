#!/usr/bin/env python3
"""
trilium_api.py — Trilium Notes ETAPI client for AI agents.

Commands:
  create            Create a note (legacy, uses AI Inbox)
  create-with-clone Create a note in category hierarchy + clone to today's day note
  ensure-category   Find or create a category in the knowledge base hierarchy
  get-structure     Fetch KB hierarchy with recent notes per category
  add-relation      Create a relation between two notes
  find-or-create-day Get today's day note via calendar API
  find-related      Search for notes with matching topic labels
  search            Search notes
  get               Get a note by ID
  update            Update note content
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import date

# --- Keychain integration ---

KEYCHAIN_SCRIPT = os.path.expanduser("~/.claude/skills/apple-keychain/scripts/keychain_helper.sh")
KEYCHAIN_SERVICE = "claude-skill-trilium"
KEYCHAIN_ACCOUNT = "etapi-token"


# --- Category definitions ---

CATEGORIES = {
    "languages": {
        "title": "Languages & Frameworks",
        "icon": "bx bx-code-alt",
        "description": "TypeScript, Angular, Python, JavaScript, CSS, HTML, and framework-specific notes.",
    },
    "architecture": {
        "title": "Architecture & Patterns",
        "icon": "bx bx-sitemap",
        "description": "Design patterns, ADRs, system design, API design, data modeling.",
    },
    "debugging": {
        "title": "Debugging & Troubleshooting",
        "icon": "bx bx-bug",
        "description": "Bug investigations, root cause analyses, error resolutions.",
    },
    "tools": {
        "title": "Tools & DevOps",
        "icon": "bx bx-wrench",
        "description": "Git, Docker, CI/CD, AWS, Terraform, CLI tools.",
    },
    "snippets": {
        "title": "Code Snippets",
        "icon": "bx bx-code-block",
        "description": "Reusable code patterns, one-liners, utility functions.",
    },
    "projects": {
        "title": "Projects",
        "icon": "bx bx-folder-open",
        "description": "Per-project notes and documentation.",
    },
}

NOTE_TYPE_ICONS = {
    "til": "bx bx-bulb",
    "debug": "bx bx-bug",
    "adr": "bx bx-sitemap",
    "snippet": "bx bx-code-block",
    "research": "bx bx-search-alt",
}

KB_ROOT_TITLE = "Engineering Knowledge Base"
KB_ROOT_ICON = "bx bx-brain"


def resolve_etapi_token(config: dict) -> str:
    """Resolve the ETAPI token: try keychain first, fall back to config file."""
    # 1. Try macOS Keychain
    if os.path.exists(KEYCHAIN_SCRIPT):
        try:
            result = subprocess.run(
                ["bash", KEYCHAIN_SCRIPT, "get", "--service", KEYCHAIN_SERVICE, "--account", KEYCHAIN_ACCOUNT],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # 2. Fall back to plaintext in config
    token = config.get("etapi_token", "")
    if token:
        print("WARNING: Using plaintext etapi_token from config. Run 'keychain-setup' to migrate to macOS Keychain.", file=sys.stderr)
        return token

    print("ERROR: No ETAPI token found. Run the 'keychain-setup' command to store it securely.", file=sys.stderr)
    sys.exit(1)


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        config = json.load(f)
    # Resolve token (keychain > config file)
    config["etapi_token"] = resolve_etapi_token(config)
    return config


def save_config(config_path: str, config: dict):
    """Save config, stripping the runtime-resolved etapi_token to avoid leaking secrets."""
    safe = {k: v for k, v in config.items() if k != "etapi_token"}
    with open(config_path, "w") as f:
        json.dump(safe, f, indent=2)
        f.write("\n")


BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def api_request(
    config: dict,
    method: str,
    endpoint: str,
    data: dict | str | None = None,
    content_type: str = "application/json",
) -> dict | str:
    url = f"{config['server_url']}/etapi{endpoint}"
    headers = {
        "Authorization": config["etapi_token"],
        "User-Agent": BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    body = None
    if data is not None:
        if isinstance(data, dict):
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            body = data.encode("utf-8")
            headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            if not resp_body.strip():
                return ""
            try:
                return json.loads(resp_body)
            except json.JSONDecodeError:
                return resp_body
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} — {e.reason}", file=sys.stderr)
        print(f"Response: {error_body[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Connection failed — {e.reason}", file=sys.stderr)
        print(
            f"Check that your Trilium server is running at {config['server_url']}",
            file=sys.stderr,
        )
        sys.exit(1)


def add_label(config: dict, note_id: str, name: str, value: str):
    """Add a label attribute to a note."""
    try:
        api_request(
            config,
            "POST",
            "/attributes",
            {
                "noteId": note_id,
                "type": "label",
                "name": name,
                "value": value,
            },
        )
    except SystemExit:
        print(f"WARNING: Failed to add label {name}={value}", file=sys.stderr)


def add_relation(config: dict, source_id: str, name: str, target_id: str):
    """Add a relation attribute between two notes."""
    try:
        api_request(
            config,
            "POST",
            "/attributes",
            {
                "noteId": source_id,
                "type": "relation",
                "name": name,
                "value": target_id,
            },
        )
    except SystemExit:
        print(
            f"WARNING: Failed to add relation {name} -> {target_id}", file=sys.stderr
        )


def create_branch(config: dict, note_id: str, parent_note_id: str) -> dict | str:
    """Clone a note under a different parent (create a branch)."""
    return api_request(
        config,
        "POST",
        "/branches",
        {
            "noteId": note_id,
            "parentNoteId": parent_note_id,
        },
    )


def search_notes(config: dict, query: str) -> list:
    """Search for notes and return results list."""
    result = api_request(
        config, "GET", "/notes?" + urllib.parse.urlencode({"search": query})
    )
    if isinstance(result, dict):
        return result.get("results", [])
    return []


def find_note_by_title(config: dict, title: str, parent_id: str | None = None) -> str | None:
    """Find a note by exact title. Optionally filter by parent."""
    query = f'note.title="{title}"'
    if parent_id:
        query += f" AND note.parents.noteId={parent_id}"
    results = search_notes(config, query)
    for note in results:
        if note.get("title") == title:
            return note["noteId"]
    return None


def get_or_create_kb_root(config: dict, config_path: str) -> str:
    """Find or create the Engineering Knowledge Base root note."""
    # Check config cache first
    root_id = config.get("knowledge_base_root")
    if root_id and root_id != "auto":
        # Verify it still exists
        try:
            resp = api_request(config, "GET", f"/notes/{root_id}")
            if isinstance(resp, dict) and resp.get("noteId"):
                return root_id
        except SystemExit:
            pass  # Note gone, recreate

    # Search for it
    existing = find_note_by_title(config, KB_ROOT_TITLE)
    if existing:
        config["knowledge_base_root"] = existing
        save_config(config_path, config)
        return existing

    # Create it
    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": "root",
            "title": KB_ROOT_TITLE,
            "type": "text",
            "content": "<p>Knowledge base managed by Claude agent. Notes are organized by topic and linked to the calendar.</p>",
        },
    )
    root_id = resp.get("note", {}).get("noteId", "")
    if root_id:
        add_label(config, root_id, "iconClass", KB_ROOT_ICON)
        config["knowledge_base_root"] = root_id
        save_config(config_path, config)
    return root_id


def ensure_category(config: dict, config_path: str, category: str) -> str:
    """Find or create a category note under the KB root. Returns the category noteId."""
    if category not in CATEGORIES:
        print(f"ERROR: Unknown category '{category}'. Valid: {', '.join(CATEGORIES.keys())}", file=sys.stderr)
        sys.exit(1)

    # Check config cache
    categories = config.get("categories", {})
    cached_id = categories.get(category)
    if cached_id and cached_id != "auto":
        # Verify it still exists
        try:
            resp = api_request(config, "GET", f"/notes/{cached_id}")
            if isinstance(resp, dict) and resp.get("noteId"):
                return cached_id
        except SystemExit:
            pass

    # Get KB root first
    root_id = get_or_create_kb_root(config, config_path)

    # Search for existing category
    cat_info = CATEGORIES[category]
    existing = find_note_by_title(config, cat_info["title"], parent_id=root_id)
    if existing:
        if "categories" not in config:
            config["categories"] = {}
        config["categories"][category] = existing
        save_config(config_path, config)
        return existing

    # Create category
    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": root_id,
            "title": cat_info["title"],
            "type": "text",
            "content": f"<p>{cat_info['description']}</p>",
        },
    )
    cat_id = resp.get("note", {}).get("noteId", "")
    if cat_id:
        add_label(config, cat_id, "iconClass", cat_info["icon"])
        if "categories" not in config:
            config["categories"] = {}
        config["categories"][category] = cat_id
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


# --- Commands ---


def cmd_create(args):
    """Legacy create command — puts notes in AI Inbox."""
    config = load_config(args.config)

    parent_id = args.parent
    if not parent_id or parent_id == "auto":
        parent_id = find_or_create_inbox(config)

    content = args.content
    if content == "-":
        content = sys.stdin.read()

    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": parent_id,
            "title": args.title,
            "type": args.type,
            "content": content,
        },
    )

    note_id = resp.get("note", {}).get("noteId", "")
    if not note_id:
        print(f"ERROR: Unexpected response: {json.dumps(resp, indent=2)}", file=sys.stderr)
        sys.exit(1)

    add_label(config, note_id, "pushDate", date.today().isoformat())
    add_label(config, note_id, "source", "claude-agent")

    if args.labels:
        for pair in args.labels.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                add_label(config, note_id, k.strip(), v.strip())

    result = {
        "status": "success",
        "noteId": note_id,
        "title": args.title,
        "parentNoteId": parent_id,
        "url": f"{config['server_url']}/#/notes/{note_id}",
    }
    print(json.dumps(result, indent=2))


def cmd_create_with_clone(args):
    """Create a note in the category hierarchy + clone to today's day note."""
    config = load_config(args.config)

    # 1. Ensure category exists
    category_id = ensure_category(config, args.config, args.category)

    # 2. Read content
    content = args.content
    if content == "-":
        content = sys.stdin.read()

    # 3. Create note under category
    resp = api_request(
        config,
        "POST",
        "/create-note",
        {
            "parentNoteId": category_id,
            "title": args.title,
            "type": args.type,
            "content": content,
        },
    )

    note_id = resp.get("note", {}).get("noteId", "")
    if not note_id:
        print(f"ERROR: Unexpected response: {json.dumps(resp, indent=2)}", file=sys.stderr)
        sys.exit(1)

    # 4. Add labels
    today = date.today().isoformat()
    add_label(config, note_id, "pushDate", today)
    add_label(config, note_id, "source", "claude-agent")
    add_label(config, note_id, "category", args.category)

    if args.note_type:
        add_label(config, note_id, "noteType", args.note_type)
        icon = NOTE_TYPE_ICONS.get(args.note_type)
        if icon:
            add_label(config, note_id, "iconClass", icon)

    if args.topic:
        for topic in args.topic.split(","):
            topic = topic.strip()
            if topic:
                add_label(config, note_id, "topic", topic)

    if args.project:
        add_label(config, note_id, "project", args.project)

    if args.labels:
        for pair in args.labels.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                add_label(config, note_id, k.strip(), v.strip())

    # 5. Clone to today's day note
    day_note_id = ""
    if not args.no_clone:
        try:
            day_note_id = get_day_note(config, today)
            if day_note_id:
                create_branch(config, note_id, day_note_id)
        except SystemExit:
            print("WARNING: Failed to clone to day note", file=sys.stderr)

    # 6. Create relations to related notes
    if args.topic and not args.no_relations:
        topics = [t.strip() for t in args.topic.split(",") if t.strip()]
        related = find_related_notes(config, topics, exclude_id=note_id)
        for rel_note in related:
            rel_id = rel_note.get("noteId", "")
            if rel_id:
                add_relation(config, note_id, "relatedTo", rel_id)

    # 7. Output result
    result = {
        "status": "success",
        "noteId": note_id,
        "title": args.title,
        "category": args.category,
        "parentNoteId": category_id,
        "dayNoteId": day_note_id,
        "clonedToDay": bool(day_note_id and not args.no_clone),
        "url": f"{config['server_url']}/#/notes/{note_id}",
    }
    print(json.dumps(result, indent=2))


def cmd_ensure_category(args):
    """Find or create a category in the hierarchy."""
    config = load_config(args.config)
    cat_id = ensure_category(config, args.config, args.category)
    print(json.dumps({"status": "success", "category": args.category, "noteId": cat_id}))


def cmd_add_relation(args):
    """Create a relation between two notes."""
    config = load_config(args.config)
    add_relation(config, args.source_id, args.name, args.target_id)
    print(json.dumps({
        "status": "success",
        "source": args.source_id,
        "relation": args.name,
        "target": args.target_id,
    }))


def cmd_find_or_create_day(args):
    """Get today's day note via calendar API."""
    config = load_config(args.config)
    day = args.day or date.today().isoformat()
    day_id = get_day_note(config, day)
    print(json.dumps({"status": "success", "day": day, "noteId": day_id}))


def cmd_find_related(args):
    """Search for notes with matching topic labels."""
    config = load_config(args.config)
    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    related = find_related_notes(config, topics, exclude_id=args.exclude or "")
    print(json.dumps({
        "status": "success",
        "topics": topics,
        "related": [{"noteId": n.get("noteId"), "title": n.get("title")} for n in related],
    }, indent=2))


def cmd_keychain_setup(args):
    """Set up or migrate ETAPI token to macOS Keychain."""
    if not os.path.exists(KEYCHAIN_SCRIPT):
        print("ERROR: apple-keychain skill not found at", KEYCHAIN_SCRIPT, file=sys.stderr)
        print("Install it first: ~/.claude/skills/apple-keychain/", file=sys.stderr)
        sys.exit(1)

    # Check if token already in keychain
    check = subprocess.run(
        ["bash", KEYCHAIN_SCRIPT, "exists", "--service", KEYCHAIN_SERVICE, "--account", KEYCHAIN_ACCOUNT],
        capture_output=True, timeout=10,
    )

    if check.returncode == 0:
        print("ETAPI token already exists in macOS Keychain.")
        print(f"  Service: {KEYCHAIN_SERVICE}")
        print(f"  Account: {KEYCHAIN_ACCOUNT}")
        return

    # Try to migrate from config file
    token = ""
    if args.config:
        try:
            with open(args.config) as f:
                cfg = json.load(f)
            token = cfg.get("etapi_token", "")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    if token:
        print(f"Found plaintext token in config. Migrating to macOS Keychain...")
        result = subprocess.run(
            ["bash", KEYCHAIN_SCRIPT, "set", "--service", KEYCHAIN_SERVICE, "--account", KEYCHAIN_ACCOUNT, "--secret", token],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            # Remove token from config file
            with open(args.config) as f:
                cfg = json.load(f)
            cfg.pop("etapi_token", None)
            with open(args.config, "w") as f:
                json.dump(cfg, f, indent=2)
                f.write("\n")
            print("OK: Token migrated to Keychain and removed from config.json")
        else:
            print(f"ERROR: Failed to store in keychain: {result.stderr}", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive setup
        print("No token found. Running interactive setup...")
        result = subprocess.run(
            ["bash", KEYCHAIN_SCRIPT, "setup", "--service", KEYCHAIN_SERVICE, "--account", KEYCHAIN_ACCOUNT,
             "--prompt", "Enter your Trilium ETAPI token"],
            timeout=60,
        )
        if result.returncode != 0:
            sys.exit(1)

    print("\nDone. The Trilium skill will now read the token from macOS Keychain.")


def cmd_get_structure(args):
    """Fetch the KB hierarchy: categories + recent notes per category."""
    config = load_config(args.config)
    limit = args.limit or 10

    root_id = config.get("knowledge_base_root")
    if not root_id or root_id == "auto":
        print(json.dumps({"status": "error", "message": "Knowledge base not set up yet. Run ensure-category first."}))
        return

    # Verify root exists
    try:
        root = api_request(config, "GET", f"/notes/{root_id}")
        if not isinstance(root, dict) or not root.get("noteId"):
            print(json.dumps({"status": "error", "message": f"KB root {root_id} not found"}))
            return
    except SystemExit:
        print(json.dumps({"status": "error", "message": f"KB root {root_id} not accessible"}))
        return

    categories_config = config.get("categories", {})
    structure = {
        "status": "success",
        "root": {"noteId": root_id, "title": KB_ROOT_TITLE},
        "categories": [],
    }

    for cat_key, cat_info in CATEGORIES.items():
        cat_id = categories_config.get(cat_key)
        if not cat_id or cat_id == "auto":
            structure["categories"].append({
                "key": cat_key,
                "title": cat_info["title"],
                "noteId": None,
                "notes": [],
            })
            continue

        # Fetch recent child notes for this category
        recent_notes = []
        try:
            results = search_notes(config, f"note.parents.noteId={cat_id} orderBy:dateModified desc limit:{limit}")
            for note in results:
                note_entry = {"noteId": note.get("noteId"), "title": note.get("title")}
                recent_notes.append(note_entry)
        except SystemExit:
            pass

        structure["categories"].append({
            "key": cat_key,
            "title": cat_info["title"],
            "noteId": cat_id,
            "noteCount": len(recent_notes),
            "recentNotes": recent_notes,
        })

    print(json.dumps(structure, indent=2))


def cmd_search(args):
    config = load_config(args.config)
    results = search_notes(config, args.query)
    print(json.dumps(results, indent=2))


def cmd_get(args):
    config = load_config(args.config)
    resp = api_request(config, "GET", f"/notes/{args.note_id}")
    print(json.dumps(resp, indent=2))


def cmd_update(args):
    config = load_config(args.config)
    content = args.content
    if content == "-":
        content = sys.stdin.read()

    content_type = "text/html" if args.type == "text" else "text/plain"
    api_request(config, "PUT", f"/notes/{args.note_id}/content", content, content_type=content_type)
    print(json.dumps({"status": "success", "noteId": args.note_id, "action": "updated"}))


def main():
    parser = argparse.ArgumentParser(description="Trilium Notes ETAPI client")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- create (legacy) ---
    p_create = sub.add_parser("create", help="Create a note (legacy, AI Inbox)")
    p_create.add_argument("--config", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--content", required=True, help="Use '-' for stdin")
    p_create.add_argument("--type", default="text", choices=["text", "code", "book"])
    p_create.add_argument("--parent", default="auto")
    p_create.add_argument("--labels", default="")
    p_create.set_defaults(func=cmd_create)

    # --- create-with-clone ---
    p_cwc = sub.add_parser("create-with-clone", help="Create note in hierarchy + clone to day")
    p_cwc.add_argument("--config", required=True)
    p_cwc.add_argument("--title", required=True)
    p_cwc.add_argument("--content", required=True, help="Use '-' for stdin")
    p_cwc.add_argument("--type", default="text", choices=["text", "code", "book"])
    p_cwc.add_argument("--category", required=True, choices=list(CATEGORIES.keys()))
    p_cwc.add_argument("--topic", default="", help="Comma-separated topics (e.g., typescript,angular)")
    p_cwc.add_argument("--note-type", default="", choices=["til", "debug", "adr", "snippet", "research", ""])
    p_cwc.add_argument("--project", default="")
    p_cwc.add_argument("--labels", default="")
    p_cwc.add_argument("--no-clone", action="store_true", help="Skip cloning to day note")
    p_cwc.add_argument("--no-relations", action="store_true", help="Skip auto-creating relations")
    p_cwc.set_defaults(func=cmd_create_with_clone)

    # --- ensure-category ---
    p_ec = sub.add_parser("ensure-category", help="Find or create a category")
    p_ec.add_argument("--config", required=True)
    p_ec.add_argument("--category", required=True, choices=list(CATEGORIES.keys()))
    p_ec.set_defaults(func=cmd_ensure_category)

    # --- add-relation ---
    p_ar = sub.add_parser("add-relation", help="Create a relation between notes")
    p_ar.add_argument("--config", required=True)
    p_ar.add_argument("--source-id", required=True)
    p_ar.add_argument("--name", required=True, help="Relation name (e.g., relatedTo)")
    p_ar.add_argument("--target-id", required=True)
    p_ar.set_defaults(func=cmd_add_relation)

    # --- find-or-create-day ---
    p_day = sub.add_parser("find-or-create-day", help="Get day note via calendar API")
    p_day.add_argument("--config", required=True)
    p_day.add_argument("--day", default="", help="ISO date (default: today)")
    p_day.set_defaults(func=cmd_find_or_create_day)

    # --- find-related ---
    p_fr = sub.add_parser("find-related", help="Find notes with matching topics")
    p_fr.add_argument("--config", required=True)
    p_fr.add_argument("--topics", required=True, help="Comma-separated topics")
    p_fr.add_argument("--exclude", default="", help="Note ID to exclude")
    p_fr.set_defaults(func=cmd_find_related)

    # --- keychain-setup ---
    p_ks = sub.add_parser("keychain-setup", help="Set up or migrate ETAPI token to macOS Keychain")
    p_ks.add_argument("--config", default="", help="Path to config.json (for migration)")
    p_ks.set_defaults(func=cmd_keychain_setup)

    # --- get-structure ---
    p_gs = sub.add_parser("get-structure", help="Fetch KB hierarchy with recent notes per category")
    p_gs.add_argument("--config", required=True)
    p_gs.add_argument("--limit", type=int, default=10, help="Max recent notes per category (default: 10)")
    p_gs.set_defaults(func=cmd_get_structure)

    # --- search ---
    p_search = sub.add_parser("search", help="Search notes")
    p_search.add_argument("--config", required=True)
    p_search.add_argument("--query", required=True)
    p_search.set_defaults(func=cmd_search)

    # --- get ---
    p_get = sub.add_parser("get", help="Get a note by ID")
    p_get.add_argument("--config", required=True)
    p_get.add_argument("--note-id", required=True)
    p_get.set_defaults(func=cmd_get)

    # --- update ---
    p_update = sub.add_parser("update", help="Update note content")
    p_update.add_argument("--config", required=True)
    p_update.add_argument("--note-id", required=True)
    p_update.add_argument("--content", required=True, help="Use '-' for stdin")
    p_update.add_argument("--type", default="text", choices=["text", "code"])
    p_update.set_defaults(func=cmd_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
