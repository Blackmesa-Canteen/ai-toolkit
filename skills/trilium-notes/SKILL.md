---
name: trilium-notes
description: "Push notes, knowledge snippets, code references, meeting summaries, and research findings to a self-hosted Trilium Notes server via ETAPI. Use this skill whenever the user wants to save, persist, record, capture, log, or push any piece of knowledge, note, snippet, finding, or learning to Trilium. Also trigger when the user says 'save this to Trilium', 'create a note', 'log this', 'persist this knowledge', 'push to my knowledge base', 'add to my notes', or references Trilium Notes in any way. Even if the user just says 'save this for later' or 'remember this', consider using this skill if Trilium is their configured knowledge base."
---

# Trilium Notes ETAPI Skill — Engineering Knowledge Base

This skill enables Claude to push content to a self-hosted Trilium Notes instance via ETAPI. Notes are organized into a **structured, interconnected knowledge base** with topic hierarchy, calendar integration, note archetypes, rich labels, and relations for note-map visualization.

## Configuration

**Always read the config first** before any API calls:

```
references/config.json
```

Fields: `server_url`, `knowledge_base_root` (auto-created if `"auto"`), `categories` (auto-populated with noteIds on first use).

### ETAPI Token (Secure Storage)

The ETAPI token is stored in **macOS Keychain** (not in config.json). The Python script resolves the token automatically:

1. **Keychain** (preferred): Stored under service `claude-skill-trilium`, account `etapi-token`
2. **Config fallback**: If keychain entry is missing, falls back to `etapi_token` in config.json (with a warning)

#### First-Time Setup or Migration

If the token isn't in the keychain yet (or needs migration from plaintext config):

```bash
python3 <skill_dir>/scripts/trilium_api.py keychain-setup --config <skill_dir>/references/config.json
```

This will:
- If a plaintext `etapi_token` exists in config.json: migrate it to Keychain and remove from config
- If no token exists anywhere: prompt the user interactively to enter it

The `apple-keychain` skill (`~/.claude/skills/apple-keychain/`) provides the underlying keychain operations.

## Knowledge Base Hierarchy

Notes are organized under a root note called **Engineering Knowledge Base** with these categories:

```
Engineering Knowledge Base/         (#iconClass=bx bx-brain)
├── Languages & Frameworks/         (#iconClass=bx bx-code-alt)
├── Architecture & Patterns/        (#iconClass=bx bx-sitemap)
├── Debugging & Troubleshooting/    (#iconClass=bx bx-bug)
├── Tools & DevOps/                 (#iconClass=bx bx-wrench)
├── Code Snippets/                  (#iconClass=bx bx-code-block)
└── Projects/                       (#iconClass=bx bx-folder-open)
```

The hierarchy is auto-created on first use. Category noteIds are cached in `config.json` after creation.

### Category Auto-Detection

When the user asks to save a note, analyze the content and pick the best category:

| Category | When to use |
|----------|------------|
| `languages` | TypeScript, Angular, Python, Rust, JavaScript, CSS, HTML, framework-specific |
| `architecture` | Design patterns, ADRs, system design, API design, data modeling |
| `debugging` | Bug investigations, root cause analysis, error resolutions, troubleshooting |
| `tools` | Git, Docker, CI/CD, AWS, Terraform, CLI tools, DevOps |
| `snippets` | Reusable code patterns, one-liners, utility functions, config templates |
| `projects` | Project-specific notes (vantage-wa, contract-compliance-checker, uxo, etc.) |

If unsure, default to `languages` for code-heavy content or `architecture` for design discussions.

## Note Archetypes

Every note must use one of these 5 archetypes. Each has a consistent HTML template and icon.

### 1. TIL (Today I Learned)

Quick insight with context, code example, and takeaway.

- **Label**: `#noteType=til`
- **Icon**: `bx bx-bulb`
- **Template**:

```html
<h2>Context</h2>
<p>[Where/how this was discovered]</p>

<h2>Insight</h2>
<p>[The key learning]</p>
<pre><code class="language-[lang]">[code example if applicable]</code></pre>

<h2>Takeaway</h2>
<p>[Why this matters, when to apply it]</p>
```

### 2. Debug Log

Problem investigation with root cause and fix.

- **Label**: `#noteType=debug`
- **Icon**: `bx bx-bug`
- **Template**:

```html
<h2>Problem</h2>
<p>[What went wrong, symptoms, error messages]</p>

<h2>Investigation</h2>
<p>[Steps taken to diagnose]</p>

<h2>Root Cause</h2>
<p>[Why it happened]</p>

<h2>Fix</h2>
<pre><code class="language-[lang]">[the fix]</code></pre>
<p>[Explanation of the fix]</p>
```

### 3. Architecture Decision (ADR)

Context, decision, and consequences.

- **Label**: `#noteType=adr`
- **Icon**: `bx bx-sitemap`
- **Template**:

```html
<h2>Context</h2>
<p>[What situation or problem prompted this decision]</p>

<h2>Decision</h2>
<p>[What was decided and why]</p>

<h2>Consequences</h2>
<ul>
  <li>[Positive/negative/neutral consequence]</li>
</ul>
```

### 4. Code Snippet

Reusable code with description and usage example.

- **Label**: `#noteType=snippet`
- **Icon**: `bx bx-code-block`
- **Template**:

```html
<h2>Description</h2>
<p>[What this snippet does]</p>

<h2>Code</h2>
<pre><code class="language-[lang]">[the snippet]</code></pre>

<h2>Usage</h2>
<pre><code class="language-[lang]">[how to use it]</code></pre>
```

### 5. Research / Deep Dive

Summary of research with key findings and references.

- **Label**: `#noteType=research`
- **Icon**: `bx bx-search-alt`
- **Template**:

```html
<h2>Summary</h2>
<p>[Brief overview of what was researched]</p>

<h2>Key Findings</h2>
<ul>
  <li>[Finding 1]</li>
  <li>[Finding 2]</li>
</ul>

<h2>Details</h2>
<p>[Extended analysis, comparisons, benchmarks]</p>

<h2>References</h2>
<ul>
  <li><a href="[url]">[title]</a></li>
</ul>
```

## Labeling Strategy

Every note gets these labels automatically:

| Label | Value | Purpose |
|-------|-------|---------|
| `#category` | `languages`, `architecture`, `debugging`, `tools`, `snippets`, `projects` | Topic bucket |
| `#topic` | Specific technology (e.g., `typescript`, `angular`, `maplibre`, `aws`) | Fine-grained search |
| `#noteType` | `til`, `debug`, `adr`, `snippet`, `research` | Archetype |
| `#source` | `claude-agent` | Auto-applied |
| `#pushDate` | ISO date | Auto-applied |
| `#iconClass` | Per-archetype icon | Visual identification |
| `#project` | Project name if applicable (e.g., `vantage-wa`) | Project scoping |

## Calendar Integration (Cloning)

**Every note is cloned to today's day note** so users can browse chronologically via Trilium's calendar widget.

The workflow:
1. Create the note under its topic category
2. Get today's day note via `GET /etapi/calendar/days/{YYYY-MM-DD}`
3. Clone (branch) the note under the day note via `POST /etapi/branches`

This means each note appears in **two places**: the topic hierarchy AND the calendar. Trilium handles this natively via branches (clones).

## Relations for Note Map

When a note references a concept that has existing notes, create `~relatedTo` relations so the note map shows connections.

After creating a note, search for other notes with matching `#topic` labels and create bidirectional relations:
- `POST /etapi/attributes` with `type: "relation"`, `name: "relatedTo"`, `value: <target_note_id>`

Only create relations to notes that share a `#topic` label. Limit to 5 relations per note to avoid noise.

## Workflow

When the user asks to save something to Trilium:

### Step 1: Read Config

```bash
cat <skill_dir>/references/config.json
```

### Step 2: Fetch Current Structure

Before deciding on category/archetype, **fetch the existing KB structure** to see what's already there. This helps with better placement and deduplication:

```bash
python3 <skill_dir>/scripts/trilium_api.py get-structure \
  --config <skill_dir>/references/config.json \
  --limit 10
```

This returns each category with its recent notes (up to 10 per category). Use this to:
- **Avoid duplicates**: If a similar note already exists, update it or adjust the title
- **Pick the right category**: See where related notes already live
- **Improve relations**: Know what existing notes share topics with the new one

### Step 3: Analyze Content

With the structure context in mind, determine:
- **Category**: Which hierarchy bucket? (languages, architecture, debugging, tools, snippets, projects)
- **Archetype**: Which note template? (til, debug, adr, snippet, research)
- **Topics**: What specific technologies/concepts? (e.g., typescript, angular, aws)
- **Project**: Is this project-specific? (e.g., vantage-wa)
- **Title**: Concise but descriptive. "TypeScript: Discriminated Unions for Error Handling" not "Note about TS".

### Step 4: Format Content

Use the archetype template from above. Convert content to clean HTML:
- Wrap paragraphs in `<p>` tags
- Use `<h2>` for template sections
- Use `<pre><code class="language-xxx">` for code blocks
- Use `<ul>/<li>` for lists
- HTML-escape any special characters in content (`<`, `>`, `&`, `"`)

### Step 5: Create the Note with Cloning

Use the Python script which handles everything — hierarchy creation, labeling, calendar cloning, and relations:

```bash
echo '<html content>' | python3 <skill_dir>/scripts/trilium_api.py create-with-clone \
  --config <skill_dir>/references/config.json \
  --title "Note Title" \
  --content - \
  --category languages \
  --topic "typescript,angular" \
  --note-type til \
  --project vantage-wa
```

Or use the shell wrapper:

```bash
echo '<html content>' | bash <skill_dir>/scripts/trilium_push.sh \
  --config <skill_dir>/references/config.json \
  --title "Note Title" \
  --category languages \
  --topic "typescript,angular" \
  --note-type til \
  --project vantage-wa \
  --clone-to-day
```

**Always pipe content via stdin** to avoid shell escaping issues with HTML content.

### Step 6: Confirm to User

Show the user:
- Note title and archetype
- Category it was filed under
- Topics applied
- Direct link to the note in Trilium
- Whether it was cloned to today's calendar

## Legacy Compatibility

The old `create` command and `--parent auto` (AI Inbox) still work for backward compatibility. New notes should always use `create-with-clone` with a `--category`.

## Error Handling

If the API call fails:
- **401 Unauthorized**: Token is wrong or expired. Tell the user to check their ETAPI token in Trilium (Options -> ETAPI).
- **404 Not Found**: The parentNoteId doesn't exist. The script will auto-create the hierarchy.
- **Connection refused**: Server is down or URL is wrong. Tell the user to verify their server is running.

Always show the user what was saved (title + brief summary) and confirm success or report the error clearly.
