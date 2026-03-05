#!/usr/bin/env python3
"""
commands.py — All cmd_* command handlers for Trilium Notes ETAPI skill.

Imports from client.py and hierarchy.py.
"""

import json
import os
import subprocess
import sys
from datetime import date

from client import (
    KEYCHAIN_SCRIPT,
    KEYCHAIN_SERVICE,
    KEYCHAIN_ACCOUNT,
    add_label,
    add_relation,
    api_request,
    create_branch,
    load_config,
    save_config,
    search_notes,
)
from hierarchy import (
    _resolve_domain,
    ensure_category,
    find_or_create_inbox,
    find_related_notes,
    get_day_note,
    get_or_create_domain_root,
)


# --- Domain CRUD ---


def cmd_list_domains(args):
    """List all domains from config."""
    config = load_config(args.config)
    domains = config.get("domains", {})
    result = []
    for key, entry in domains.items():
        result.append({
            "key": key,
            "title": entry.get("title", key),
            "icon": entry.get("icon", ""),
            "description": entry.get("description", ""),
            "noteId": entry.get("noteId"),
            "categoryCount": len(entry.get("categories", {})),
        })
    print(json.dumps({"status": "success", "domains": result}, indent=2))


def cmd_create_domain(args):
    """Add a new domain to config + create Trilium root note."""
    config = load_config(args.config)
    domains = config.get("domains", {})

    if args.key in domains:
        print(f"ERROR: Domain '{args.key}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Add to config with placeholder noteId
    domains[args.key] = {
        "noteId": "auto",
        "title": args.title,
        "icon": args.icon,
        "description": args.description or "",
        "categories": {},
    }
    config["domains"] = domains
    save_config(args.config, config)

    # Create in Trilium
    root_id = get_or_create_domain_root(config, args.config, args.key)

    print(json.dumps({
        "status": "success",
        "action": "created",
        "key": args.key,
        "title": args.title,
        "icon": args.icon,
        "noteId": root_id,
    }, indent=2))


def cmd_delete_domain(args):
    """Remove a domain from config only (Trilium note preserved)."""
    config = load_config(args.config)
    domains = config.get("domains", {})

    if args.key not in domains:
        print(f"ERROR: Domain '{args.key}' not found in config.", file=sys.stderr)
        sys.exit(1)

    removed = domains.pop(args.key)
    config["domains"] = domains
    save_config(args.config, config)

    note_id = removed.get("noteId")
    print(json.dumps({
        "status": "success",
        "action": "deleted_from_config",
        "key": args.key,
        "noteId": note_id,
        "message": "Domain removed from config. Trilium note preserved.",
    }, indent=2))


def cmd_rename_domain(args):
    """Update domain metadata in config + PATCH Trilium note title/icon."""
    config = load_config(args.config)
    domains = config.get("domains", {})

    if args.key not in domains:
        print(f"ERROR: Domain '{args.key}' not found in config.", file=sys.stderr)
        sys.exit(1)

    entry = domains[args.key]

    if args.title:
        entry["title"] = args.title
    if args.icon:
        entry["icon"] = args.icon
    if args.description is not None:
        entry["description"] = args.description

    domains[args.key] = entry
    config["domains"] = domains
    save_config(args.config, config)

    # PATCH Trilium note if noteId exists
    note_id = entry.get("noteId")
    if note_id and note_id != "auto":
        patch_data = {}
        if args.title:
            patch_data["title"] = args.title
        if patch_data:
            try:
                api_request(config, "PATCH", f"/notes/{note_id}", patch_data)
            except SystemExit:
                print("WARNING: Failed to update Trilium note title.", file=sys.stderr)
        if args.icon:
            add_label(config, note_id, "iconClass", args.icon)

    print(json.dumps({
        "status": "success",
        "action": "updated",
        "key": args.key,
        "entry": {k: v for k, v in entry.items() if k != "categories"},
    }, indent=2))


# --- Category CRUD (with --domain) ---


def cmd_list_categories(args):
    """List all categories from a domain's config."""
    config = load_config(args.config)
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    domain = config["domains"][domain_key]
    categories = domain.get("categories", {})
    result = []
    for key, entry in categories.items():
        if isinstance(entry, dict):
            result.append({
                "key": key,
                "title": entry.get("title", key),
                "icon": entry.get("icon", ""),
                "description": entry.get("description", ""),
                "noteId": entry.get("noteId"),
            })
        else:
            result.append({"key": key, "noteId": entry})
    print(json.dumps({"status": "success", "domain": domain_key, "categories": result}, indent=2))


def cmd_create_category(args):
    """Add a new category to a domain + create Trilium note."""
    config = load_config(args.config)
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    domain = config["domains"][domain_key]
    categories = domain.get("categories", {})

    if args.key in categories:
        print(f"ERROR: Category '{args.key}' already exists in domain '{domain_key}'.", file=sys.stderr)
        sys.exit(1)

    # Add to config with placeholder noteId
    categories[args.key] = {
        "noteId": "auto",
        "title": args.title,
        "icon": args.icon,
        "description": args.description or "",
    }
    domain["categories"] = categories
    config["domains"][domain_key] = domain
    save_config(args.config, config)

    # Create in Trilium
    cat_id = ensure_category(config, args.config, domain_key, args.key)

    print(json.dumps({
        "status": "success",
        "action": "created",
        "domain": domain_key,
        "key": args.key,
        "title": args.title,
        "icon": args.icon,
        "noteId": cat_id,
    }, indent=2))


def cmd_delete_category(args):
    """Remove a category from a domain's config only (Trilium note preserved)."""
    config = load_config(args.config)
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    domain = config["domains"][domain_key]
    categories = domain.get("categories", {})

    if args.key not in categories:
        print(f"ERROR: Category '{args.key}' not found in domain '{domain_key}'.", file=sys.stderr)
        sys.exit(1)

    removed = categories.pop(args.key)
    domain["categories"] = categories
    config["domains"][domain_key] = domain
    save_config(args.config, config)

    note_id = removed.get("noteId") if isinstance(removed, dict) else removed
    print(json.dumps({
        "status": "success",
        "action": "deleted_from_config",
        "domain": domain_key,
        "key": args.key,
        "noteId": note_id,
        "message": "Category removed from config. Trilium note preserved.",
    }, indent=2))


def cmd_rename_category(args):
    """Update category metadata in a domain's config + PATCH Trilium note title/icon."""
    config = load_config(args.config)
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    domain = config["domains"][domain_key]
    categories = domain.get("categories", {})

    if args.key not in categories:
        print(f"ERROR: Category '{args.key}' not found in domain '{domain_key}'.", file=sys.stderr)
        sys.exit(1)

    entry = categories[args.key]
    if not isinstance(entry, dict):
        entry = {"noteId": entry, "title": args.key, "icon": "", "description": ""}

    if args.title:
        entry["title"] = args.title
    if args.icon:
        entry["icon"] = args.icon
    if args.description is not None:
        entry["description"] = args.description

    categories[args.key] = entry
    domain["categories"] = categories
    config["domains"][domain_key] = domain
    save_config(args.config, config)

    # PATCH Trilium note if noteId exists
    note_id = entry.get("noteId")
    if note_id and note_id != "auto":
        patch_data = {}
        if args.title:
            patch_data["title"] = args.title
        if patch_data:
            try:
                api_request(config, "PATCH", f"/notes/{note_id}", patch_data)
            except SystemExit:
                print("WARNING: Failed to update Trilium note title.", file=sys.stderr)
        if args.icon:
            add_label(config, note_id, "iconClass", args.icon)

    print(json.dumps({
        "status": "success",
        "action": "updated",
        "domain": domain_key,
        "key": args.key,
        "entry": entry,
    }, indent=2))


# --- Note operations ---


def cmd_create(args):
    """Legacy create command — puts notes in AI Inbox."""
    config = load_config(args.config)

    parent_id = args.parent
    if not parent_id or parent_id == "auto":
        parent_id = find_or_create_inbox(config)

    content = args.content
    if content == "-":
        content = sys.stdin.read()

    # Auto-detect MIME type
    mime = getattr(args, "mime", "") or ""
    if not mime:
        _mime_map = {
            "mermaid": "text/vnd.mermaid",
            "canvas": "application/json",
            "mindMap": "application/json",
        }
        mime = _mime_map.get(args.type, "")

    create_data = {
        "parentNoteId": parent_id,
        "title": args.title,
        "type": args.type,
        "content": content,
    }
    if mime:
        create_data["mime"] = mime

    resp = api_request(
        config,
        "POST",
        "/create-note",
        create_data,
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

    # 1. Resolve domain and ensure category
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    category_id = ensure_category(config, args.config, domain_key, args.category)

    # 2. Read content
    content = args.content
    if content == "-":
        content = sys.stdin.read()

    # 3. Auto-detect MIME type
    mime = getattr(args, "mime", "") or ""
    if not mime:
        _mime_map = {
            "mermaid": "text/vnd.mermaid",
            "canvas": "application/json",
            "mindMap": "application/json",
        }
        mime = _mime_map.get(args.type, "")

    create_data = {
        "parentNoteId": category_id,
        "title": args.title,
        "type": args.type,
        "content": content,
    }
    if mime:
        create_data["mime"] = mime

    # 4. Create note under category
    resp = api_request(
        config,
        "POST",
        "/create-note",
        create_data,
    )

    note_id = resp.get("note", {}).get("noteId", "")
    if not note_id:
        print(f"ERROR: Unexpected response: {json.dumps(resp, indent=2)}", file=sys.stderr)
        sys.exit(1)

    # 5. Add labels
    today = date.today().isoformat()
    add_label(config, note_id, "pushDate", today)
    add_label(config, note_id, "source", "claude-agent")
    add_label(config, note_id, "category", args.category)
    add_label(config, note_id, "domain", domain_key)

    if args.note_type:
        add_label(config, note_id, "noteType", args.note_type)
        # Look up icon from note_types config
        note_types = config.get("note_types", {})
        nt_entry = note_types.get(args.note_type, {})
        icon = nt_entry.get("icon") if isinstance(nt_entry, dict) else None
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

    # 6. Clone to today's day note
    day_note_id = ""
    if not args.no_clone:
        try:
            day_note_id = get_day_note(config, today)
            if day_note_id:
                create_branch(config, note_id, day_note_id)
        except SystemExit:
            print("WARNING: Failed to clone to day note", file=sys.stderr)

    # 7. Create relations to related notes
    if args.topic and not args.no_relations:
        topics = [t.strip() for t in args.topic.split(",") if t.strip()]
        related = find_related_notes(config, topics, exclude_id=note_id)
        for rel_note in related:
            rel_id = rel_note.get("noteId", "")
            if rel_id:
                add_relation(config, note_id, "relatedTo", rel_id)

    # 8. Output result
    result = {
        "status": "success",
        "noteId": note_id,
        "title": args.title,
        "domain": domain_key,
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
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    cat_id = ensure_category(config, args.config, domain_key, args.category)
    print(json.dumps({"status": "success", "domain": domain_key, "category": args.category, "noteId": cat_id}))


def cmd_move_note(args):
    """Re-parent a note between categories (optionally cross-domain)."""
    config = load_config(args.config)

    # Resolve source and target domains
    domain_key = _resolve_domain(config, getattr(args, "domain", None))
    target_domain_key = getattr(args, "target_domain", None) or domain_key
    if target_domain_key not in config.get("domains", {}):
        print(f"ERROR: Target domain '{target_domain_key}' not found.", file=sys.stderr)
        sys.exit(1)

    target_domain = config["domains"][target_domain_key]
    target_categories = target_domain.get("categories", {})

    # Validate target category
    if args.target_category not in target_categories:
        print(f"ERROR: Target category '{args.target_category}' not found in domain '{target_domain_key}'. Run 'list-categories --domain {target_domain_key}'.", file=sys.stderr)
        sys.exit(1)

    # Ensure target category note exists
    target_cat_id = ensure_category(config, args.config, target_domain_key, args.target_category)

    # GET note to verify it exists
    note = api_request(config, "GET", f"/notes/{args.note_id}")
    if not isinstance(note, dict) or not note.get("noteId"):
        print(f"ERROR: Note '{args.note_id}' not found.", file=sys.stderr)
        sys.exit(1)

    # Build map of all known category noteIds across relevant domains
    known_cat_ids = {}
    source_domain = config["domains"][domain_key]
    for ckey, centry in source_domain.get("categories", {}).items():
        cid = centry.get("noteId") if isinstance(centry, dict) else centry
        if cid and cid != "auto":
            known_cat_ids[cid] = ckey

    # Determine source category
    source_cat_key = args.source_category
    source_branch_id = None

    # Get branches for this note
    branches = api_request(config, "GET", f"/notes/{args.note_id}/branches")
    if isinstance(branches, list):
        for branch in branches:
            parent_id = branch.get("parentNoteId", "")
            if source_cat_key:
                src_entry = source_domain.get("categories", {}).get(source_cat_key, {})
                src_id = src_entry.get("noteId") if isinstance(src_entry, dict) else src_entry
                if parent_id == src_id:
                    source_branch_id = branch.get("branchId")
                    break
            else:
                if parent_id in known_cat_ids:
                    source_cat_key = known_cat_ids[parent_id]
                    source_branch_id = branch.get("branchId")
                    break

    # Delete old branch
    if source_branch_id:
        try:
            api_request(config, "DELETE", f"/branches/{source_branch_id}")
        except SystemExit:
            print(f"WARNING: Failed to delete old branch {source_branch_id}.", file=sys.stderr)

    # Create new branch under target category
    create_branch(config, args.note_id, target_cat_id)

    # Update #category label
    attrs = api_request(config, "GET", f"/notes/{args.note_id}/attributes")
    if isinstance(attrs, list):
        for attr in attrs:
            if attr.get("type") == "label" and attr.get("name") == "category":
                try:
                    api_request(config, "DELETE", f"/attributes/{attr['attributeId']}")
                except SystemExit:
                    pass
                break
    add_label(config, args.note_id, "category", args.target_category)

    # Update #domain label if cross-domain move
    if target_domain_key != domain_key:
        if isinstance(attrs, list):
            for attr in attrs:
                if attr.get("type") == "label" and attr.get("name") == "domain":
                    try:
                        api_request(config, "DELETE", f"/attributes/{attr['attributeId']}")
                    except SystemExit:
                        pass
                    break
        add_label(config, args.note_id, "domain", target_domain_key)

    print(json.dumps({
        "status": "success",
        "action": "moved",
        "noteId": args.note_id,
        "fromDomain": domain_key,
        "fromCategory": source_cat_key or "unknown",
        "toDomain": target_domain_key,
        "toCategory": args.target_category,
        "targetCategoryNoteId": target_cat_id,
    }, indent=2))


def cmd_get_structure(args):
    """Fetch hierarchy: all domains with categories + recent notes per category."""
    config = load_config(args.config)
    limit = args.limit or 10
    domains = config.get("domains", {})

    structure = {
        "status": "success",
        "domains": [],
    }

    for domain_key, domain in domains.items():
        domain_root_id = domain.get("noteId")
        domain_title = domain.get("title", domain_key)
        domain_icon = domain.get("icon", "")
        domain_desc = domain.get("description", "")

        # Verify root exists
        if not domain_root_id or domain_root_id == "auto":
            structure["domains"].append({
                "key": domain_key,
                "title": domain_title,
                "icon": domain_icon,
                "description": domain_desc,
                "noteId": None,
                "categories": [],
            })
            continue

        try:
            root = api_request(config, "GET", f"/notes/{domain_root_id}")
            if not isinstance(root, dict) or not root.get("noteId"):
                domain_root_id = None
        except SystemExit:
            domain_root_id = None

        categories_config = domain.get("categories", {})
        cat_list = []

        for cat_key, cat_entry in categories_config.items():
            cat_title = cat_entry.get("title", cat_key) if isinstance(cat_entry, dict) else cat_key
            cat_icon = cat_entry.get("icon", "") if isinstance(cat_entry, dict) else ""
            cat_desc = cat_entry.get("description", "") if isinstance(cat_entry, dict) else ""
            cat_id = cat_entry.get("noteId") if isinstance(cat_entry, dict) else cat_entry

            if not cat_id or cat_id == "auto":
                cat_list.append({
                    "key": cat_key,
                    "title": cat_title,
                    "icon": cat_icon,
                    "description": cat_desc,
                    "noteId": None,
                    "notes": [],
                })
                continue

            # Fetch recent child notes
            recent_notes = []
            try:
                results = search_notes(config, f"note.parents.noteId={cat_id} orderBy:dateModified desc limit:{limit}")
                for note in results:
                    recent_notes.append({"noteId": note.get("noteId"), "title": note.get("title")})
            except SystemExit:
                pass

            cat_list.append({
                "key": cat_key,
                "title": cat_title,
                "icon": cat_icon,
                "description": cat_desc,
                "noteId": cat_id,
                "noteCount": len(recent_notes),
                "recentNotes": recent_notes,
            })

        structure["domains"].append({
            "key": domain_key,
            "title": domain_title,
            "icon": domain_icon,
            "description": domain_desc,
            "noteId": domain_root_id,
            "categories": cat_list,
        })

    print(json.dumps(structure, indent=2))


# --- Utility commands (unchanged logic) ---


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
        print("No token found. Running interactive setup...")
        result = subprocess.run(
            ["bash", KEYCHAIN_SCRIPT, "setup", "--service", KEYCHAIN_SERVICE, "--account", KEYCHAIN_ACCOUNT,
             "--prompt", "Enter your Trilium ETAPI token"],
            timeout=60,
        )
        if result.returncode != 0:
            sys.exit(1)

    print("\nDone. The Trilium skill will now read the token from macOS Keychain.")


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

    # Use application/octet-stream to bypass Cloudflare WAF OWASP rules
    # that block raw HTML bodies (rule 949110: Inbound Anomaly Score Exceeded)
    api_request(config, "PUT", f"/notes/{args.note_id}/content", content, content_type="application/octet-stream")
    print(json.dumps({"status": "success", "noteId": args.note_id, "action": "updated"}))


def cmd_list_note_types(args):
    """List all note types from config."""
    config = load_config(args.config)
    note_types = config.get("note_types", {})
    result = []
    for key, entry in note_types.items():
        if isinstance(entry, dict):
            result.append({
                "key": key,
                "icon": entry.get("icon", ""),
                "description": entry.get("description", ""),
            })
        else:
            result.append({"key": key, "icon": entry})
    print(json.dumps({"status": "success", "noteTypes": result}, indent=2))


def cmd_create_note_type(args):
    """Add a new note type to config."""
    config = load_config(args.config)
    note_types = config.get("note_types", {})

    if args.key in note_types:
        print(f"ERROR: Note type '{args.key}' already exists.", file=sys.stderr)
        sys.exit(1)

    note_types[args.key] = {
        "icon": args.icon,
        "description": args.description or "",
    }
    config["note_types"] = note_types
    save_config(args.config, config)

    print(json.dumps({
        "status": "success",
        "action": "created",
        "key": args.key,
        "icon": args.icon,
        "description": args.description or "",
    }, indent=2))
