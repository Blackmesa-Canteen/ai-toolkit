# AI Toolkit

A collection of skills, connectors, plugins, and MCP servers for AI coding assistants.

## What's Inside

| Category | Description | Status |
|----------|-------------|--------|
| [Skills](skills/) | Claude Code skills for automating workflows | Available |
| [Connectors](connectors/) | Integrations with external services | Coming soon |
| [Plugins](plugins/) | Extensions for AI assistants | Coming soon |
| [MCP Servers](mcp-servers/) | Model Context Protocol servers | Coming soon |

## Available Skills

### [trilium-notes](skills/trilium-notes/)

Push notes, knowledge snippets, code references, and research findings to a self-hosted [Trilium Notes](https://github.com/zadam/trilium) server via ETAPI. Organizes content into a structured knowledge base with topic hierarchy, calendar integration, note archetypes, and rich labels.

### [apple-keychain](skills/apple-keychain/)

Securely store and retrieve secrets (API tokens, passwords, credentials) using the macOS Keychain. Designed to be called by other skills that need secret management.

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- macOS (for the apple-keychain skill)

### Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/ai-toolkit.git ~/projects/ai-toolkit

# Symlink skills into Claude Code
ln -s ~/projects/ai-toolkit/skills/trilium-notes ~/.claude/skills/trilium-notes
ln -s ~/projects/ai-toolkit/skills/apple-keychain ~/.claude/skills/apple-keychain
```

### Trilium Notes Setup

```bash
# Copy the example config
cd ~/.claude/skills/trilium-notes/references
cp config.example.json config.json
# Edit config.json with your Trilium server URL

# Store your ETAPI token securely in macOS Keychain
python3 ~/.claude/skills/trilium-notes/scripts/trilium_api.py keychain-setup
```

## License

MIT
