# Hindi Textbook Extraction System Design

**Date:** 2026-01-09
**Status:** Validated (Codex review complete)

## Overview

Extract structured data from Hindi textbook markdown into JSON files for:
1. **Anki card generation** - Vocabulary with examples, inflections
2. **Practice prompt generation** - ~10k word reference doc for Gemini sessions
3. **Curriculum tracking** - Grammar concepts with prerequisites, exercises

## Data Flow

```
study-materials/textbook/*.md
        |
        v (instructor + Pydantic)
study-materials/extracted/
    |-- units/
    |   |-- 01.json
    |   |-- 02.json
    |   `-- ...
    `-- index.json

Runtime:
+----------------+     +-----------------+     +----------------+
|  Anki          |     |  Extracted JSON |     |  Goals MCP     |
|  (vocab cards) |     |  (all content)  |     |  (completion)  |
+-------+--------+     +--------+--------+     +-------+--------+
        |                       |                      |
        +----------+------------+----------+-----------+
                   |                       |
                   v                       v
            Practice Prompt         Progress Dashboard
            (~10k words)
```

## Schema

See: `scripts/hindi_schemas.py`

### Models

| Model | Purpose |
|-------|---------|
| `VocabularyEntry` | Word with hindi, transliteration, meaning, gender, oblique forms, verb_forms |
| `GrammarConcept` | Rule with explanation, examples, prerequisites, difficulty |
| `Exercise` | Practice item with type, items, concepts_practiced |
| `Section` | Unit subsection (dialogue or grammar) |
| `Unit` | Container for all content from one chapter |

### Key Design Decisions

1. **UUID for IDs** - Stable identifiers that survive re-extraction
2. **Separate anki_note_id** - Decoupled from content ID for sync
3. **source_ref on everything** - Traceability to textbook section
4. **VerbForms as optional nested model** - Keeps nouns clean
5. **Enums for types** - SectionType, ExerciseType, PartOfSpeech, etc.
6. **Priority/Difficulty ratings** - Enable filtered practice prompts

## Storage Format

```json
// units/03.json
{
  "unit_number": 3,
  "title": "Rooms in the house",
  "sections": [
    {"id": "...", "slug": "3a", "label": "Pratap's mother phones", "section_type": "dialogue", "order": 1},
    {"id": "...", "slug": "3.1", "label": "Simple postpositions", "section_type": "grammar", "order": 2}
  ],
  "vocabulary": [...],
  "concepts": [...],
  "exercises": [...]
}

// index.json
{
  "units": [
    {"unit_number": 1, "title": "...", "vocab_count": 45, "concept_count": 8, "exercise_count": 6}
  ],
  "total_vocab": 892,
  "total_concepts": 156
}
```

## Integration Points

### Anki (via AnkiConnect)
- Query mastery by `anki_note_id`
- Create cards from `VocabularyEntry`
- Card fields: hindi, transliteration, meaning, gender, examples

### Goals MCP
- Track concept completion (done/in-progress)
- Track exercise completion
- Store in existing todo/progress infrastructure

### Practice Prompt Generator
- Input: learned vocab (from Anki), completed concepts (from Goals MCP)
- Output: ~10k word reference document + session config
- Format: 80% cumulative knowledge + 20% conversation guidance

## Next Steps

1. Build extraction script using instructor
2. Extract all 18 units
3. Build Anki sync script
4. Build practice prompt generator
5. Add MCP tools for Hindi learning
