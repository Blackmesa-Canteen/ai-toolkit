---
name: trilium-notes
description: "Push notes, knowledge snippets, code references, meeting summaries, and research findings to a self-hosted Trilium Notes server via ETAPI. Use this skill whenever the user wants to save, persist, record, capture, log, or push any piece of knowledge, note, snippet, finding, or learning to Trilium. Also trigger when the user says 'save this to Trilium', 'create a note', 'log this', 'persist this knowledge', 'push to my knowledge base', 'add to my notes', or references Trilium Notes in any way. Even if the user just says 'save this for later' or 'remember this', consider using this skill if Trilium is their configured knowledge base."
---

# Trilium Notes ETAPI Skill — Knowledge Base

This skill enables Claude to push content to a self-hosted Trilium Notes instance via ETAPI. Notes are organized into **multiple knowledge domains** with topic hierarchy, calendar integration, note archetypes, rich labels, and relations for note-map visualization.

## Configuration

**Always read the config first** before any API calls:

```
references/config.json
```

Fields: `server_url`, `domains` (nested domain → categories structure), `note_types` (global archetypes).

Each domain is a top-level note under Trilium root (alongside Trilium defaults like Journal, Miscellaneous). Categories live under their domain's root note.

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

Notes are organized under **domains** — top-level root notes in Trilium. Each domain contains **categories** which hold the actual notes. Domains are config-driven and auto-created on first use.

Example structure in Trilium:
```
root
├── Engineering Knowledge Base    ← domain "engineering"
│   ├── Languages & Frameworks    ← category "languages"
│   ├── Architecture & Patterns   ← category "architecture"
│   └── ...
├── Daily Life                    ← domain "daily_life"
│   ├── Health & Fitness          ← category "health"
│   └── ...
├── Journal                       ← Trilium default (not managed)
└── Miscellaneous                 ← Trilium default (not managed)
```

### Domain Selection Workflow

**Always run `list-domains` first** to see available domains:

```bash
python3 <skill_dir>/scripts/trilium_api.py list-domains --config <skill_dir>/references/config.json
```

Then:
1. Analyze content to determine which domain it belongs to
2. If one domain fits: use it
3. If no domain fits: propose a new domain to the user, then create it:

```bash
python3 <skill_dir>/scripts/trilium_api.py create-domain \
  --config <skill_dir>/references/config.json \
  --key daily_life --title "Daily Life" --icon "bx bx-home" \
  --description "Health, finance, cooking, hobbies, personal."
```

### Category Selection Workflow

**After selecting a domain, run `list-categories`**:

```bash
python3 <skill_dir>/scripts/trilium_api.py list-categories \
  --config <skill_dir>/references/config.json --domain engineering
```

Then:
1. Analyze content against each category's title and description
2. If one fits: use it
3. If borderline: pick the closest match and mention it to the user
4. If nothing fits: propose a new category to the user, then create it:

```bash
python3 <skill_dir>/scripts/trilium_api.py create-category \
  --config <skill_dir>/references/config.json --domain engineering \
  --key ml --title "Machine Learning" --icon "bx bx-brain" \
  --description "ML models, training, inference, data pipelines."
```

If unsure, default to `languages` for code-heavy content or `architecture` for design discussions.

## Note Archetypes

These are the built-in archetypes. Custom types can be added via `create-note-type`. Run `list-note-types` to see all available types.

Every note must use one of these archetypes. Each has a consistent HTML template and icon.

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
| `#domain` | Key from `list-domains` output | Domain bucket |
| `#category` | Key from `list-categories` output | Topic bucket |
| `#topic` | Specific technology (e.g., `typescript`, `angular`, `maplibre`, `aws`) | Fine-grained search |
| `#noteType` | Key from `list-note-types` output | Archetype |
| `#source` | `claude-agent` | Auto-applied |
| `#pushDate` | ISO date | Auto-applied |
| `#iconClass` | Per-archetype icon (from config) | Visual identification |
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

### Step 2: Fetch Domains, Categories, Note Types & Structure

Before deciding on domain/category/archetype, run these commands (can be parallel):

```bash
# List available domains
python3 <skill_dir>/scripts/trilium_api.py list-domains --config <skill_dir>/references/config.json

# List categories for the target domain
python3 <skill_dir>/scripts/trilium_api.py list-categories \
  --config <skill_dir>/references/config.json --domain engineering

# List note types
python3 <skill_dir>/scripts/trilium_api.py list-note-types --config <skill_dir>/references/config.json

# Fetch existing hierarchy with recent notes per domain/category
python3 <skill_dir>/scripts/trilium_api.py get-structure \
  --config <skill_dir>/references/config.json \
  --limit 10
```

Use the structure output to:
- **Avoid duplicates**: If a similar note already exists, update it or adjust the title
- **Pick the right domain and category**: See where related notes already live
- **Improve relations**: Know what existing notes share topics with the new one

### Step 3: Analyze Content

With the structure context in mind, determine:
- **Domain**: Which knowledge domain? (engineering, daily_life, etc.)
- **Category**: Which hierarchy bucket? (languages, architecture, debugging, tools, snippets, projects)
- **Archetype**: Which note template? (til, debug, adr, snippet, research)
- **Topics**: What specific technologies/concepts? (e.g., typescript, angular, aws)
- **Project**: Is this project-specific? (e.g., vantage-wa)
- **Title**: Concise but descriptive. "TypeScript: Discriminated Unions for Error Handling" not "Note about TS".

#### Visual Format Evaluation

Before defaulting to HTML text, evaluate whether the content is better represented visually:

| If the content contains... | Consider using | Read |
|---------------------------|---------------|------|
| Process flows, sequences, decision trees | Mermaid diagram | `trilium-content` formats.md section 1 |
| Hierarchical breakdown, brainstorming, topic trees | Mind Map | `trilium-content` formats.md section 3 |
| Architecture drawings, freeform spatial layouts | Canvas (Excalidraw) | `trilium-content` formats.md section 2 |
| Entity relationships, dependency graphs | Relation Map | `trilium-content` formats.md section 4 |
| Location data, places, coordinates | Geo Map | `trilium-content` formats.md section 5 |

If visual format is appropriate:
1. **Ask the user for confirmation** before proceeding:
   - Suggest the visual format and explain why (e.g., "This process flow would work well as a Mermaid diagram — shall I create it as a diagram instead of plain text?")
   - If the user confirms: read `~/.claude/skills/trilium-content/references/formats.md` for the format spec, generate content, use `--type mermaid|canvas|mindMap|relationMap`
   - If the user declines: proceed with the default `text` type and HTML template

If the user **explicitly requests** a visual format ("make a diagram", "create a mindmap"), skip the confirmation and use the visual format directly.

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
  --domain engineering \
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
  --domain engineering \
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
- Domain and category it was filed under
- Topics applied
- Direct link to the note in Trilium
- Whether it was cloned to today's calendar

## Legacy Compatibility

The old `create` command and `--parent auto` (AI Inbox) still work for backward compatibility. New notes should always use `create-with-clone` with `--domain` and `--category`.

The `--domain` flag is optional when only one domain exists — it auto-selects.

## Domain Management

Domains are top-level notes under Trilium root. Each domain has its own set of categories.

```bash
# List all domains
python3 <skill_dir>/scripts/trilium_api.py list-domains --config <skill_dir>/references/config.json

# Create a new domain (also creates the Trilium root note)
python3 <skill_dir>/scripts/trilium_api.py create-domain \
  --config <skill_dir>/references/config.json \
  --key daily_life --title "Daily Life" --icon "bx bx-home" \
  --description "Health, finance, cooking, hobbies, personal."

# Update a domain's title, icon, or description
python3 <skill_dir>/scripts/trilium_api.py rename-domain \
  --config <skill_dir>/references/config.json \
  --key engineering --title "Software Engineering" --icon "bx bx-code"

# Remove a domain from config (Trilium note is preserved — safe default)
python3 <skill_dir>/scripts/trilium_api.py delete-domain \
  --config <skill_dir>/references/config.json --key daily_life
```

## Category & Note Type Management

Categories are stored under their domain in `config.json` and managed via CRUD commands. The Trilium server + config.json is the source of truth.

### Categories

```bash
# List all categories for a domain
python3 <skill_dir>/scripts/trilium_api.py list-categories \
  --config <skill_dir>/references/config.json --domain engineering

# Create a new category (also creates the Trilium note)
python3 <skill_dir>/scripts/trilium_api.py create-category \
  --config <skill_dir>/references/config.json --domain engineering \
  --key security --title "Security & Auth" --icon "bx bx-shield" \
  --description "Authentication, authorization, encryption, security practices."

# Update a category's title, icon, or description
python3 <skill_dir>/scripts/trilium_api.py rename-category \
  --config <skill_dir>/references/config.json --domain engineering \
  --key tools --title "Tools & Infrastructure" --icon "bx bx-server"

# Remove a category from config (Trilium note is preserved — safe default)
python3 <skill_dir>/scripts/trilium_api.py delete-category \
  --config <skill_dir>/references/config.json --domain engineering --key snippets
```

### Moving Notes Between Categories

```bash
# Move a note within the same domain
python3 <skill_dir>/scripts/trilium_api.py move-note \
  --config <skill_dir>/references/config.json \
  --domain engineering \
  --note-id ABC123 --target-category geospatial

# Move with explicit source category
python3 <skill_dir>/scripts/trilium_api.py move-note \
  --config <skill_dir>/references/config.json \
  --domain engineering \
  --note-id ABC123 --target-category geospatial --source-category languages

# Cross-domain move
python3 <skill_dir>/scripts/trilium_api.py move-note \
  --config <skill_dir>/references/config.json \
  --domain engineering --target-domain daily_life \
  --note-id ABC123 --target-category health
```

### Note Types

```bash
# List all note types
python3 <skill_dir>/scripts/trilium_api.py list-note-types --config <skill_dir>/references/config.json

# Create a custom note type
python3 <skill_dir>/scripts/trilium_api.py create-note-type \
  --config <skill_dir>/references/config.json \
  --key howto --icon "bx bx-list-check" --description "Step-by-step how-to guide."
```

## Advanced Content Types

This skill supports all TriliumNext note types via `--type`:
`text`, `code`, `book`, `mermaid`, `canvas`, `mindMap`, `relationMap`, `render`.

MIME is auto-detected for mermaid (`text/vnd.mermaid`), canvas and mindMap (`application/json`).
Override with `--mime` if needed.

For detailed format specs, generation rules, and examples for each visual type,
read `~/.claude/skills/trilium-content/references/formats.md`.

## Error Handling

If the API call fails:
- **401 Unauthorized**: Token is wrong or expired. Tell the user to check their ETAPI token in Trilium (Options -> ETAPI).
- **404 Not Found**: The parentNoteId doesn't exist. The script will auto-create the hierarchy.
- **Connection refused**: Server is down or URL is wrong. Tell the user to verify their server is running.

Always show the user what was saved (title + brief summary) and confirm success or report the error clearly.
