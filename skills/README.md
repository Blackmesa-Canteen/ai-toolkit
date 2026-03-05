# Skills

[Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) are reusable capabilities that extend what Claude can do in your terminal. Each skill is a directory containing a `SKILL.md` file (which tells Claude when and how to use the skill) and supporting scripts.

## Available Skills

- **[trilium-notes](trilium-notes/)** — Push structured notes to a Trilium Notes knowledge base via ETAPI
- **[apple-keychain](apple-keychain/)** — Secure secret management using macOS Keychain

## Installing a Skill

Symlink the skill directory into `~/.claude/skills/`:

```bash
ln -s /path/to/ai-toolkit/skills/<skill-name> ~/.claude/skills/<skill-name>
```

Claude Code automatically discovers skills in `~/.claude/skills/`.

## Creating a New Skill

1. Create a directory under `skills/` with a descriptive name
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and usage instructions
3. Add any helper scripts under `scripts/`
4. Add reference files or config templates under `references/`
