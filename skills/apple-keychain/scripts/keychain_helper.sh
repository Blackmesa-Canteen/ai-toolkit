#!/usr/bin/env bash
# keychain_helper.sh — Manage secrets in macOS Keychain
#
# Commands:
#   get    --service <s> --account <a>              Retrieve a secret (stdout)
#   set    --service <s> --account <a> [--secret v] Store/update a secret
#   delete --service <s> --account <a>              Remove a secret
#   exists --service <s> --account <a>              Check existence (exit code)
#   setup  --service <s> --account <a> [--prompt p] Interactive first-time setup

set -euo pipefail

# --- Parse command and arguments ---
COMMAND="${1:-}"
shift 2>/dev/null || true

SERVICE=""
ACCOUNT=""
SECRET=""
PROMPT_MSG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE="$2"; shift 2 ;;
    --account) ACCOUNT="$2"; shift 2 ;;
    --secret)  SECRET="$2"; shift 2 ;;
    --prompt)  PROMPT_MSG="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$COMMAND" ]]; then
  echo "Usage: keychain_helper.sh <get|set|delete|exists|setup> --service <s> --account <a>" >&2
  exit 1
fi

if [[ -z "$SERVICE" || -z "$ACCOUNT" ]]; then
  echo "ERROR: --service and --account are required" >&2
  exit 1
fi

# --- Commands ---

case "$COMMAND" in
  get)
    # Retrieve password from keychain, output to stdout
    PASSWORD=$(security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w 2>/dev/null) || {
      echo "ERROR: Secret not found for service='$SERVICE' account='$ACCOUNT'" >&2
      echo "Run 'setup' to store it first." >&2
      exit 1
    }
    echo "$PASSWORD"
    ;;

  set)
    # Read from stdin if --secret not provided
    if [[ -z "$SECRET" ]]; then
      if [[ -t 0 ]]; then
        echo "ERROR: No secret provided. Use --secret or pipe via stdin." >&2
        exit 1
      fi
      SECRET=$(cat)
    fi

    if [[ -z "$SECRET" ]]; then
      echo "ERROR: Secret value is empty" >&2
      exit 1
    fi

    # Use -U to update if exists, otherwise add
    security add-generic-password \
      -s "$SERVICE" \
      -a "$ACCOUNT" \
      -w "$SECRET" \
      -U \
      -l "Claude Skill: $SERVICE / $ACCOUNT" \
      -j "Managed by Claude Code apple-keychain skill" 2>/dev/null || {
      echo "ERROR: Failed to store secret in keychain" >&2
      exit 1
    }
    echo "OK: Secret stored for service='$SERVICE' account='$ACCOUNT'"
    ;;

  delete)
    security delete-generic-password -s "$SERVICE" -a "$ACCOUNT" 2>/dev/null || {
      echo "WARNING: Secret not found (may already be deleted)" >&2
      exit 0
    }
    echo "OK: Secret deleted for service='$SERVICE' account='$ACCOUNT'"
    ;;

  exists)
    # Silent check — exit 0 if found, exit 1 if not
    security find-generic-password -s "$SERVICE" -a "$ACCOUNT" >/dev/null 2>&1
    exit $?
    ;;

  setup)
    # Interactive setup flow
    DEFAULT_PROMPT="Enter secret for $SERVICE/$ACCOUNT"
    PROMPT_MSG="${PROMPT_MSG:-$DEFAULT_PROMPT}"

    # Check if already exists
    if security find-generic-password -s "$SERVICE" -a "$ACCOUNT" >/dev/null 2>&1; then
      echo "A secret already exists for service='$SERVICE' account='$ACCOUNT'."
      read -r -p "Overwrite? [y/N] " CONFIRM
      if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
        echo "Keeping existing secret."
        exit 0
      fi
    fi

    # Prompt for the secret (hidden input)
    read -r -s -p "$PROMPT_MSG: " INPUT_SECRET
    echo  # newline after hidden input

    if [[ -z "$INPUT_SECRET" ]]; then
      echo "ERROR: No value entered. Aborting." >&2
      exit 1
    fi

    # Store it
    security add-generic-password \
      -s "$SERVICE" \
      -a "$ACCOUNT" \
      -w "$INPUT_SECRET" \
      -U \
      -l "Claude Skill: $SERVICE / $ACCOUNT" \
      -j "Managed by Claude Code apple-keychain skill" 2>/dev/null || {
      echo "ERROR: Failed to store secret in keychain" >&2
      exit 1
    }
    echo "OK: Secret stored successfully."
    ;;

  *)
    echo "Unknown command: $COMMAND" >&2
    echo "Valid commands: get, set, delete, exists, setup" >&2
    exit 1
    ;;
esac
