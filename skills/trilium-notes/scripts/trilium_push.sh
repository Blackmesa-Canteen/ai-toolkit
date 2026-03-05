#!/usr/bin/env bash
# trilium_push.sh — Push a note to Trilium Notes via ETAPI
#
# Usage (new — preferred, content via stdin):
#   echo '<p>HTML content</p>' | bash trilium_push.sh \
#     --config config.json --title "Title" \
#     --category languages --topic "typescript,angular" \
#     --note-type til --clone-to-day
#
# Usage (legacy — still works):
#   bash trilium_push.sh --config config.json --title "Title" --content "HTML content"
#
# Content is read from stdin by default. Use --content to pass inline (legacy).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Parse arguments ---
CONFIG=""
TITLE=""
CONTENT=""
NOTE_TYPE="text"
PARENT_ID=""
LABELS=""
CATEGORY=""
TOPIC=""
ARCHETYPE=""
PROJECT=""
ICON=""
CLONE_TO_DAY=false
NO_RELATIONS=false
RELATIONS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)       CONFIG="$2"; shift 2 ;;
    --title)        TITLE="$2"; shift 2 ;;
    --content)      CONTENT="$2"; shift 2 ;;
    --type)         NOTE_TYPE="$2"; shift 2 ;;
    --parent)       PARENT_ID="$2"; shift 2 ;;
    --labels)       LABELS="$2"; shift 2 ;;
    --category)     CATEGORY="$2"; shift 2 ;;
    --topic)        TOPIC="$2"; shift 2 ;;
    --note-type)    ARCHETYPE="$2"; shift 2 ;;
    --project)      PROJECT="$2"; shift 2 ;;
    --icon)         ICON="$2"; shift 2 ;;
    --clone-to-day) CLONE_TO_DAY=true; shift ;;
    --no-relations) NO_RELATIONS=true; shift ;;
    --relations)    RELATIONS="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$CONFIG" || -z "$TITLE" ]]; then
  echo "ERROR: --config and --title are required" >&2
  exit 1
fi

# --- Read content from stdin if not provided via --content ---
if [[ -z "$CONTENT" ]]; then
  if [[ -t 0 ]]; then
    echo "ERROR: No content provided. Pipe content via stdin or use --content" >&2
    exit 1
  fi
  CONTENT=$(cat)
fi

if [[ -z "$CONTENT" ]]; then
  echo "ERROR: Content is empty" >&2
  exit 1
fi

# --- Route to the appropriate Python command ---

# Build common args
PYTHON_CMD="python3 ${SCRIPT_DIR}/trilium_api.py"

if [[ -n "$CATEGORY" ]]; then
  # New path: create-with-clone
  CMD_ARGS=(create-with-clone --config "$CONFIG" --title "$TITLE" --content - --type "$NOTE_TYPE" --category "$CATEGORY")

  [[ -n "$TOPIC" ]] && CMD_ARGS+=(--topic "$TOPIC")
  [[ -n "$ARCHETYPE" ]] && CMD_ARGS+=(--note-type "$ARCHETYPE")
  [[ -n "$PROJECT" ]] && CMD_ARGS+=(--project "$PROJECT")
  [[ -n "$LABELS" ]] && CMD_ARGS+=(--labels "$LABELS")
  [[ "$CLONE_TO_DAY" != "true" ]] && CMD_ARGS+=(--no-clone)
  [[ "$NO_RELATIONS" == "true" ]] && CMD_ARGS+=(--no-relations)

  echo "$CONTENT" | $PYTHON_CMD "${CMD_ARGS[@]}"
else
  # Legacy path: create under AI Inbox
  CMD_ARGS=(create --config "$CONFIG" --title "$TITLE" --content - --type "$NOTE_TYPE")

  [[ -n "$PARENT_ID" ]] && CMD_ARGS+=(--parent "$PARENT_ID")
  [[ -n "$LABELS" ]] && CMD_ARGS+=(--labels "$LABELS")

  echo "$CONTENT" | $PYTHON_CMD "${CMD_ARGS[@]}"
fi

RESULT=$?

# --- Handle manual relations if provided ---
if [[ -n "$RELATIONS" && $RESULT -eq 0 ]]; then
  echo "NOTE: Manual relations via --relations are not yet supported in shell wrapper." >&2
  echo "Use python3 trilium_api.py add-relation directly." >&2
fi

# --- Handle manual icon if provided (only for legacy path) ---
if [[ -n "$ICON" && -z "$CATEGORY" ]]; then
  echo "NOTE: --icon is only applied automatically when using --category with --note-type." >&2
fi

exit $RESULT
