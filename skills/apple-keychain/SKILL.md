---
name: apple-keychain
description: "Store and retrieve secrets (API tokens, passwords, credentials) securely using macOS Keychain. Use this skill when any other skill needs to store or retrieve a secret, when the user asks to save a credential securely, or when setting up authentication for a service. Trigger on: 'store secret', 'save API key', 'keychain', 'credential', 'secure storage', or when another skill references 'apple-keychain' for secret management."
---

# Apple Keychain Skill

Securely store and retrieve secrets (API tokens, passwords, credentials) using the macOS Keychain via the `security` CLI. This skill is designed to be called by other skills that need secret management.

## Why Use This

- **No plaintext secrets** in config files
- **OS-level encryption** — secrets are stored in the macOS login keychain
- **Access control** — only the terminal app that stored the secret can retrieve it without prompting
- **Reusable** — any skill can call the helper script

## Helper Script

All operations go through a single script:

```bash
bash <skill_dir>/scripts/keychain_helper.sh <command> [options]
```

### Commands

#### `get` — Retrieve a secret

```bash
bash <skill_dir>/scripts/keychain_helper.sh get --service "trilium-notes" --account "etapi-token"
```

Outputs the secret value to stdout. Exits with code 1 if not found.

#### `set` — Store or update a secret

```bash
bash <skill_dir>/scripts/keychain_helper.sh set --service "trilium-notes" --account "etapi-token" --secret "the-token-value"
```

If `--secret` is omitted, reads from stdin (safer for long/complex values):

```bash
echo "the-token-value" | bash <skill_dir>/scripts/keychain_helper.sh set --service "trilium-notes" --account "etapi-token"
```

#### `delete` — Remove a secret

```bash
bash <skill_dir>/scripts/keychain_helper.sh delete --service "trilium-notes" --account "etapi-token"
```

#### `exists` — Check if a secret exists (no output, exit code only)

```bash
bash <skill_dir>/scripts/keychain_helper.sh exists --service "trilium-notes" --account "etapi-token"
# Exit 0 = exists, Exit 1 = not found
```

#### `setup` — Interactive setup (prompt user, store secret)

```bash
bash <skill_dir>/scripts/keychain_helper.sh setup --service "trilium-notes" --account "etapi-token" --prompt "Enter your Trilium ETAPI token"
```

This is the recommended command for first-time setup flows. It:
1. Checks if the secret already exists
2. If it does, asks whether to overwrite
3. Prompts the user for the value (input is hidden)
4. Stores it in the keychain

### Naming Convention

Use consistent service/account naming:

| Service | Account | Description |
|---------|---------|-------------|
| `claude-skill-trilium` | `etapi-token` | Trilium ETAPI token |
| `claude-skill-<name>` | `<key-name>` | Pattern for any skill |

The `claude-skill-` prefix groups all Claude-managed secrets together.

## Integration Pattern for Other Skills

Other skills should:

1. **On first use**: Check if the secret exists. If not, run `setup` to prompt the user.
2. **On every use**: Call `get` to retrieve the secret. Never cache it in config files.

Example flow in another skill's script:

```bash
KEYCHAIN_SCRIPT="$HOME/.claude/skills/apple-keychain/scripts/keychain_helper.sh"
SERVICE="claude-skill-myservice"
ACCOUNT="api-token"

# Check + setup if needed
if ! bash "$KEYCHAIN_SCRIPT" exists --service "$SERVICE" --account "$ACCOUNT"; then
  echo "First-time setup: please enter your API token."
  bash "$KEYCHAIN_SCRIPT" setup --service "$SERVICE" --account "$ACCOUNT" --prompt "Enter API token"
fi

# Retrieve
TOKEN=$(bash "$KEYCHAIN_SCRIPT" get --service "$SERVICE" --account "$ACCOUNT")
```

## Security Notes

- Secrets are stored in the user's **login keychain** (default)
- The terminal application (Terminal.app, iTerm2, etc.) is automatically trusted for access
- Other applications will trigger a macOS permission dialog
- The `security` command may prompt for the keychain password if the keychain is locked
