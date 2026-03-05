#!/usr/bin/env python3
"""
trilium_api.py — Trilium Notes ETAPI client for AI agents.

Commands:
  create            Create a note (legacy, uses AI Inbox)
  create-with-clone Create a note in category hierarchy + clone to today's day note
  ensure-category   Find or create a category in the knowledge base hierarchy
  get-structure     Fetch hierarchy with recent notes per domain/category
  add-relation      Create a relation between two notes
  find-or-create-day Get today's day note via calendar API
  find-related      Search for notes with matching topic labels
  search            Search notes
  get               Get a note by ID
  update            Update note content
  list-domains      List all domains from config
  create-domain     Add a new domain to config + Trilium
  delete-domain     Remove a domain from config
  rename-domain     Update domain metadata in config + Trilium
  list-categories   List all categories from a domain's config
  create-category   Add a new category to a domain + Trilium
  delete-category   Remove a category from a domain's config
  rename-category   Update category metadata in config + Trilium
  move-note         Re-parent a note between categories (optionally cross-domain)
  list-note-types   List all note types from config
  create-note-type  Add a new note type to config
"""

import argparse
import sys

from commands import (
    cmd_add_relation,
    cmd_create,
    cmd_create_category,
    cmd_create_domain,
    cmd_create_note_type,
    cmd_create_with_clone,
    cmd_delete_category,
    cmd_delete_domain,
    cmd_ensure_category,
    cmd_find_or_create_day,
    cmd_find_related,
    cmd_get,
    cmd_get_structure,
    cmd_keychain_setup,
    cmd_list_categories,
    cmd_list_domains,
    cmd_list_note_types,
    cmd_move_note,
    cmd_rename_category,
    cmd_rename_domain,
    cmd_search,
    cmd_update,
)


def main():
    parser = argparse.ArgumentParser(description="Trilium Notes ETAPI client")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- create (legacy) ---
    p_create = sub.add_parser("create", help="Create a note (legacy, AI Inbox)")
    p_create.add_argument("--config", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--content", required=True, help="Use '-' for stdin")
    p_create.add_argument("--type", default="text",
        choices=["text", "code", "book", "mermaid", "canvas", "mindMap", "relationMap", "render"])
    p_create.add_argument("--mime", default="", help="MIME type (auto-detected from --type if omitted)")
    p_create.add_argument("--parent", default="auto")
    p_create.add_argument("--labels", default="")
    p_create.set_defaults(func=cmd_create)

    # --- create-with-clone ---
    p_cwc = sub.add_parser("create-with-clone", help="Create note in hierarchy + clone to day")
    p_cwc.add_argument("--config", required=True)
    p_cwc.add_argument("--title", required=True)
    p_cwc.add_argument("--content", required=True, help="Use '-' for stdin")
    p_cwc.add_argument("--type", default="text",
        choices=["text", "code", "book", "mermaid", "canvas", "mindMap", "relationMap", "render"])
    p_cwc.add_argument("--mime", default="", help="MIME type (auto-detected from --type if omitted)")
    p_cwc.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_cwc.add_argument("--category", required=True, help="Category key (run list-categories to see options)")
    p_cwc.add_argument("--topic", default="", help="Comma-separated topics (e.g., typescript,angular)")
    p_cwc.add_argument("--note-type", default="", help="Note type key (run list-note-types to see options)")
    p_cwc.add_argument("--project", default="")
    p_cwc.add_argument("--labels", default="")
    p_cwc.add_argument("--no-clone", action="store_true", help="Skip cloning to day note")
    p_cwc.add_argument("--no-relations", action="store_true", help="Skip auto-creating relations")
    p_cwc.set_defaults(func=cmd_create_with_clone)

    # --- ensure-category ---
    p_ec = sub.add_parser("ensure-category", help="Find or create a category")
    p_ec.add_argument("--config", required=True)
    p_ec.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_ec.add_argument("--category", required=True, help="Category key (run list-categories to see options)")
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
    p_gs = sub.add_parser("get-structure", help="Fetch hierarchy with recent notes per domain/category")
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

    # --- list-domains ---
    p_ld = sub.add_parser("list-domains", help="List all domains from config")
    p_ld.add_argument("--config", required=True)
    p_ld.set_defaults(func=cmd_list_domains)

    # --- create-domain ---
    p_cd = sub.add_parser("create-domain", help="Add a new domain to config + Trilium")
    p_cd.add_argument("--config", required=True)
    p_cd.add_argument("--key", required=True, help="Short key (e.g., daily_life, cooking)")
    p_cd.add_argument("--title", required=True, help="Display title (e.g., 'Daily Life')")
    p_cd.add_argument("--icon", default="bx bx-note", help="Boxicons class (default: bx bx-note)")
    p_cd.add_argument("--description", default="", help="Domain description")
    p_cd.set_defaults(func=cmd_create_domain)

    # --- delete-domain ---
    p_dd = sub.add_parser("delete-domain", help="Remove a domain from config (Trilium note preserved)")
    p_dd.add_argument("--config", required=True)
    p_dd.add_argument("--key", required=True, help="Domain key to remove")
    p_dd.set_defaults(func=cmd_delete_domain)

    # --- rename-domain ---
    p_rd = sub.add_parser("rename-domain", help="Update domain metadata in config + Trilium")
    p_rd.add_argument("--config", required=True)
    p_rd.add_argument("--key", required=True, help="Domain key to update")
    p_rd.add_argument("--title", default="", help="New display title")
    p_rd.add_argument("--icon", default="", help="New icon class")
    p_rd.add_argument("--description", default=None, help="New description")
    p_rd.set_defaults(func=cmd_rename_domain)

    # --- list-categories ---
    p_lc = sub.add_parser("list-categories", help="List all categories from a domain")
    p_lc.add_argument("--config", required=True)
    p_lc.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_lc.set_defaults(func=cmd_list_categories)

    # --- create-category ---
    p_cc = sub.add_parser("create-category", help="Add a new category to a domain + Trilium")
    p_cc.add_argument("--config", required=True)
    p_cc.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_cc.add_argument("--key", required=True, help="Short key (e.g., ml, security)")
    p_cc.add_argument("--title", required=True, help="Display title (e.g., 'Machine Learning')")
    p_cc.add_argument("--icon", default="bx bx-note", help="Boxicons class (default: bx bx-note)")
    p_cc.add_argument("--description", default="", help="Category description")
    p_cc.set_defaults(func=cmd_create_category)

    # --- delete-category ---
    p_dc = sub.add_parser("delete-category", help="Remove a category from config (Trilium note preserved)")
    p_dc.add_argument("--config", required=True)
    p_dc.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_dc.add_argument("--key", required=True, help="Category key to remove")
    p_dc.set_defaults(func=cmd_delete_category)

    # --- rename-category ---
    p_rc = sub.add_parser("rename-category", help="Update category metadata in config + Trilium")
    p_rc.add_argument("--config", required=True)
    p_rc.add_argument("--domain", default=None, help="Domain key (auto-selected if only one)")
    p_rc.add_argument("--key", required=True, help="Category key to update")
    p_rc.add_argument("--title", default="", help="New display title")
    p_rc.add_argument("--icon", default="", help="New icon class")
    p_rc.add_argument("--description", default=None, help="New description")
    p_rc.set_defaults(func=cmd_rename_category)

    # --- move-note ---
    p_mn = sub.add_parser("move-note", help="Re-parent a note between categories (optionally cross-domain)")
    p_mn.add_argument("--config", required=True)
    p_mn.add_argument("--note-id", required=True, help="Note ID to move")
    p_mn.add_argument("--domain", default=None, help="Source domain key (auto-selected if only one)")
    p_mn.add_argument("--target-domain", default=None, help="Target domain key (defaults to source domain)")
    p_mn.add_argument("--target-category", required=True, help="Target category key")
    p_mn.add_argument("--source-category", default="", help="Source category key (auto-detected if omitted)")
    p_mn.set_defaults(func=cmd_move_note)

    # --- list-note-types ---
    p_lnt = sub.add_parser("list-note-types", help="List all note types from config")
    p_lnt.add_argument("--config", required=True)
    p_lnt.set_defaults(func=cmd_list_note_types)

    # --- create-note-type ---
    p_cnt = sub.add_parser("create-note-type", help="Add a new note type to config")
    p_cnt.add_argument("--config", required=True)
    p_cnt.add_argument("--key", required=True, help="Short key (e.g., howto, checklist)")
    p_cnt.add_argument("--icon", required=True, help="Boxicons class (e.g., bx bx-list-check)")
    p_cnt.add_argument("--description", default="", help="Note type description")
    p_cnt.set_defaults(func=cmd_create_note_type)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
