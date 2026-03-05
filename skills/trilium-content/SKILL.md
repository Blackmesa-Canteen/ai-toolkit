---
name: trilium-content
description: "Generate rich visual content for TriliumNext notes — Mermaid diagrams, Canvas (Excalidraw) drawings, Mind Maps, Relation Maps, and Geo Maps. Use this skill when the user asks to draw, diagram, visualize, sketch, or create any visual/spatial content for Trilium. Also triggered indirectly by the trilium-notes skill when content is better represented visually."
---

# Trilium Content — Advanced Visual Note Types

This skill provides format specs and generation guidelines for TriliumNext's rich content types beyond plain text. It works as a companion to the `trilium-notes` skill.

## Trigger Conditions

**Direct triggers** — user says:
- "draw", "diagram", "flowchart", "mindmap", "mind map", "visualize", "sketch", "canvas", "mermaid"
- "relation map", "geo map", "pin on map", "map this location"

**Indirect triggers** — called by `trilium-notes` skill during Step 3 (Analyze Content) when the AI determines content would benefit from visual representation.

## Format Selection Guide

| Content pattern | Best format | `--type` | Why |
|----------------|------------|----------|-----|
| Process flows, sequences, state machines, decision trees | **Mermaid** | `mermaid` | Text-based, many diagram subtypes |
| Hierarchical brainstorming, topic breakdown, category trees | **Mind Map** | `mindMap` | Visual hierarchy with expandable nodes |
| Freeform diagrams, architecture drawings, UI wireframes | **Canvas (Excalidraw)** | `canvas` | Positioned shapes and arrows on infinite canvas |
| Entity relationships, family trees, dependency graphs | **Relation Map** | `relationMap` | Notes as nodes, named edges as relations |
| Location data, travel logs, places visited, pin boards | **Geo Map** | `book` + `#viewType=geoMap` | Pins on geographic map with coordinates |

## AI Judgment Criteria — When to Suggest Visual Over Text

- Content describes a **process or flow** with steps, decisions, or sequences -> Mermaid
- Content is a **hierarchical breakdown** (topic -> subtopics -> details) -> Mind Map
- Content involves **multiple entities with named relationships** -> Relation Map
- Content includes **geographic locations or coordinates** -> Geo Map
- Content describes a **spatial layout** (system architecture, UI wireframe) -> Canvas
- **When in doubt, default to text** — visual types are for content where spatial/relational structure adds clear value

## Integration Workflow

1. Determine the best content type from the guide above
2. Read `~/.claude/skills/trilium-content/references/formats.md` for the chosen format's detailed spec
3. Generate content following the spec exactly
4. Call `trilium-notes` skill's `create-with-clone` with `--type` and `--mime` (MIME is auto-detected for known types)
5. For composite types (Relation Map, Geo Map), use multiple sequential API calls

## Quick Reference — API Calls

### Mermaid

```bash
echo 'graph TD; A-->B;' | python3 <trilium-notes-skill>/scripts/trilium_api.py create-with-clone \
  --config <trilium-notes-skill>/references/config.json --domain engineering --category architecture \
  --title "Flow Diagram" --content - --type mermaid
```

### Canvas (Excalidraw)

```bash
echo '{"type":"excalidraw","version":2,"elements":[],"appState":{"viewBackgroundColor":"#ffffff"},"files":{}}' | \
  python3 <trilium-notes-skill>/scripts/trilium_api.py create-with-clone \
  --config <trilium-notes-skill>/references/config.json --domain engineering --category architecture \
  --title "Architecture Diagram" --content - --type canvas --mime "application/json"
```

### Mind Map (MindElixir)

```bash
echo '{"nodeData":{"id":"root","topic":"Topic","children":[]}}' | \
  python3 <trilium-notes-skill>/scripts/trilium_api.py create-with-clone \
  --config <trilium-notes-skill>/references/config.json --domain engineering --category architecture \
  --title "Brainstorm" --content - --type mindMap --mime "application/json"
```

### Relation Map (Composite)

```bash
# 1. Create the relation map container
python3 <trilium-notes-skill>/scripts/trilium_api.py create-with-clone \
  --config <trilium-notes-skill>/references/config.json --domain engineering --category architecture \
  --title "System Dependencies" --content "" --type relationMap --note-type research

# 2. Create child entity notes under the container (use returned noteId as parent)
# 3. Add relations between children
python3 <trilium-notes-skill>/scripts/trilium_api.py add-relation \
  --config <trilium-notes-skill>/references/config.json --source-id ABC --name "dependsOn" --target-id DEF
```

### Geo Map (Composite)

```bash
# 1. Create the geo map container
python3 <trilium-notes-skill>/scripts/trilium_api.py create-with-clone \
  --config <trilium-notes-skill>/references/config.json --domain daily_life --category travel \
  --title "Places Visited 2026" --content "" --type book --note-type research

# 2. Set viewType label on the container (use returned noteId)
# 3. Create child notes with #geolocation="lat,lng" labels
```

## Detailed Format Specs

For complete format specifications, element properties, design rules, and constraints for each content type, read:

```
~/.claude/skills/trilium-content/references/formats.md
```
