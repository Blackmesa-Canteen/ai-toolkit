#!/usr/bin/env python3
"""
client.py — Config, auth, and ETAPI primitives for Trilium Notes.

Extracted from trilium_api.py. All other modules import from here.
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import urllib.error

# --- Keychain integration ---

KEYCHAIN_SCRIPT = os.path.expanduser("~/.claude/skills/apple-keychain/scripts/keychain_helper.sh")
KEYCHAIN_SERVICE = "claude-skill-trilium"
KEYCHAIN_ACCOUNT = "etapi-token"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# --- Builtin seeds (used only during config schema migration) ---
# Runtime source of truth is config.json, not these dicts.

_BUILTIN_CATEGORIES = {
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
    "geospatial": {
        "title": "Geospatial & GIS",
        "icon": "bx bx-map-alt",
        "description": "GIS concepts, mapping technologies, coordinate systems, tile servers, COG, GDAL.",
    },
}

_BUILTIN_NOTE_TYPES = {
    "til": {"icon": "bx bx-bulb", "description": "Today I Learned — quick insight with context and takeaway."},
    "debug": {"icon": "bx bx-bug", "description": "Debug log — problem with root cause and fix."},
    "adr": {"icon": "bx bx-sitemap", "description": "Architecture Decision Record."},
    "snippet": {"icon": "bx bx-code-block", "description": "Reusable code with description and usage."},
    "research": {"icon": "bx bx-search-alt", "description": "Research/deep dive with findings and references."},
}

_BUILTIN_DOMAINS = {
    "engineering": {
        "noteId": "auto",
        "title": "Engineering Knowledge Base",
        "icon": "bx bx-brain",
        "description": "Software engineering, code, architecture, tools.",
        "categories": dict(_BUILTIN_CATEGORIES),
    },
}


# --- Token resolution ---


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


# --- Config migration ---


def _migrate_config_schema(config: dict, config_path: str) -> bool:
    """Migrate config schema. v1→v2: flat noteId strings to rich objects. v2→v3: top-level categories to nested domains."""
    migrated = False

    # v1 → v2: Migrate categories from flat string noteId to rich object
    categories = config.get("categories", {})
    for key, value in list(categories.items()):
        if isinstance(value, str):
            seed = _BUILTIN_CATEGORIES.get(key, {})
            categories[key] = {
                "noteId": value,
                "title": seed.get("title", key.replace("_", " ").title()),
                "icon": seed.get("icon", "bx bx-note"),
                "description": seed.get("description", ""),
            }
            migrated = True
    config["categories"] = categories

    # Seed note_types if absent
    if "note_types" not in config:
        config["note_types"] = dict(_BUILTIN_NOTE_TYPES)
        migrated = True

    # v2 → v3: Wrap top-level categories into domains
    if "categories" in config and "domains" not in config:
        config["domains"] = {
            "engineering": {
                "noteId": config.pop("knowledge_base_root", "auto"),
                "title": "Engineering Knowledge Base",
                "icon": "bx bx-brain",
                "description": "Software engineering, code, architecture, tools.",
                "categories": config.pop("categories"),
            }
        }
        migrated = True

    if migrated:
        save_config(config_path, config)
        print("INFO: Migrated config.json schema.", file=sys.stderr)

    return migrated


# --- Config I/O ---


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        config = json.load(f)
    # Auto-migrate schema
    _migrate_config_schema(config, config_path)
    # Resolve token (keychain > config file)
    config["etapi_token"] = resolve_etapi_token(config)
    return config


def save_config(config_path: str, config: dict):
    """Save config, stripping the runtime-resolved etapi_token to avoid leaking secrets."""
    safe = {k: v for k, v in config.items() if k != "etapi_token"}
    with open(config_path, "w") as f:
        json.dump(safe, f, indent=2)
        f.write("\n")


# --- ETAPI primitives ---


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
