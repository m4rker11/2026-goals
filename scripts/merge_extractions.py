#!/usr/bin/env python3
"""
Phase 2: Merge raw extractions into canonical vocabulary.

Reads from: study-materials/extracted/raw/*.json
Outputs to:
  - study-materials/extracted/vocabulary.json  (canonical vocab)
  - study-materials/extracted/grammar.json     (canonical grammar)
  - study-materials/extracted/units/*.json     (per-unit views)
  - study-materials/extracted/index.json       (summary)

Deduplication rules:
- Vocabulary: keyed by (canonical_hindi, part_of_speech)
- Grammar: keyed by normalized name
- First occurrence owns the entry
- Later occurrences contribute examples only

Usage:
    python scripts/merge_extractions.py
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from hindi_schemas import (
    Example,
    ExtractedIndex,
    Gender,
    GrammarConcept,
    MergedCorpus,
    PartOfSpeech,
    Priority,
    UnitSummary,
    UnitView,
    VocabularyEntry,
)


def slugify(text: str) -> str:
    """Convert text to a slug."""
    return text.lower().replace(" ", "-").replace("'", "")[:50]


def normalize_pos(pos: str) -> PartOfSpeech:
    """Normalize part of speech string to enum."""
    pos_map = {
        "noun": PartOfSpeech.NOUN,
        "verb": PartOfSpeech.VERB,
        "adj": PartOfSpeech.ADJECTIVE,
        "adjective": PartOfSpeech.ADJECTIVE,
        "adv": PartOfSpeech.ADVERB,
        "adverb": PartOfSpeech.ADVERB,
        "postposition": PartOfSpeech.POSTPOSITION,
        "pronoun": PartOfSpeech.PRONOUN,
        "conjunction": PartOfSpeech.CONJUNCTION,
        "particle": PartOfSpeech.PARTICLE,
        "interjection": PartOfSpeech.INTERJECTION,
        "compound_verb": PartOfSpeech.COMPOUND_VERB,
    }
    return pos_map.get(pos.lower(), PartOfSpeech.NOUN)


def normalize_gender(gender: str | None) -> Gender | None:
    """Normalize gender string to enum."""
    if not gender:
        return None
    if gender.lower() in ("m", "masculine"):
        return Gender.MASCULINE
    if gender.lower() in ("f", "feminine"):
        return Gender.FEMININE
    return None


def load_raw_extractions(raw_dir: Path) -> dict[int, dict]:
    """Load all raw extractions from directory."""
    extractions = {}
    for f in sorted(raw_dir.glob("*.json")):
        try:
            unit_num = int(f.stem)
            with open(f) as fp:
                data = json.load(fp)
            if "error" not in data:
                extractions[unit_num] = data
                print(f"  Loaded unit {unit_num}: {len(data.get('vocabulary', []))} vocab, {len(data.get('grammar_points', []))} grammar")
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  Skipping {f.name}: {e}")
    return extractions


def merge_vocabulary(extractions: dict[int, dict]) -> tuple[list[VocabularyEntry], dict[int, tuple[list[str], list[str]]]]:
    """
    Merge vocabulary across all units.

    Returns:
        - List of canonical VocabularyEntry
        - Dict mapping unit_num -> (new_vocab_ids, review_vocab_ids)
    """
    vocab_index: dict[tuple[str, PartOfSpeech], VocabularyEntry] = {}
    unit_vocab: dict[int, tuple[list[str], list[str]]] = {}  # unit -> (new_ids, review_ids)

    # Process units in order so earliest wins
    for unit_num in sorted(extractions.keys()):
        data = extractions[unit_num]
        new_ids = []
        review_ids = []

        for raw_vocab in data.get("vocabulary", []):
            pos = normalize_pos(raw_vocab.get("part_of_speech", "noun"))
            key = (raw_vocab["hindi"], pos)

            # Convert raw examples to Example objects with source tracking
            examples = []
            for ex in raw_vocab.get("examples", []):
                examples.append(Example(
                    hindi=ex["hindi"],
                    transliteration=ex.get("transliteration", ""),
                    english=ex["english"],
                    source_unit=unit_num,
                    source_section=None,
                ))

            if key in vocab_index:
                # Existing entry - aggregate examples, mark as review
                existing = vocab_index[key]
                existing.examples.extend(examples)
                if unit_num not in existing.units_encountered:
                    existing.units_encountered.append(unit_num)
                review_ids.append(existing.id)
            else:
                # New entry - create canonical entry
                entry_id = str(uuid.uuid4())
                entry = VocabularyEntry(
                    id=entry_id,
                    hindi=raw_vocab["hindi"],
                    transliteration=raw_vocab.get("transliteration", ""),
                    meaning=raw_vocab.get("meaning", ""),
                    part_of_speech=pos,
                    gender=normalize_gender(raw_vocab.get("gender")),
                    first_seen_unit=unit_num,
                    units_encountered=[unit_num],
                    examples=examples,
                    priority=Priority.COMMON,
                )
                vocab_index[key] = entry
                new_ids.append(entry_id)

        unit_vocab[unit_num] = (new_ids, review_ids)
        print(f"  Unit {unit_num}: {len(new_ids)} new, {len(review_ids)} review")

    return list(vocab_index.values()), unit_vocab


def merge_grammar(extractions: dict[int, dict]) -> tuple[list[GrammarConcept], dict[int, tuple[list[str], list[str]]]]:
    """
    Merge grammar concepts across all units.

    Returns:
        - List of canonical GrammarConcept
        - Dict mapping unit_num -> (new_concept_ids, review_concept_ids)
    """
    grammar_index: dict[str, GrammarConcept] = {}
    unit_grammar: dict[int, tuple[list[str], list[str]]] = {}

    for unit_num in sorted(extractions.keys()):
        data = extractions[unit_num]
        new_ids = []
        review_ids = []

        for raw_grammar in data.get("grammar_points", []):
            name = raw_grammar["name"]
            key = slugify(name)

            examples = []
            for ex in raw_grammar.get("examples", []):
                examples.append(Example(
                    hindi=ex["hindi"],
                    transliteration=ex.get("transliteration", ""),
                    english=ex["english"],
                    source_unit=unit_num,
                    source_section=None,
                ))

            if key in grammar_index:
                existing = grammar_index[key]
                existing.examples.extend(examples)
                if unit_num not in existing.units_encountered:
                    existing.units_encountered.append(unit_num)
                review_ids.append(existing.id)
            else:
                entry_id = str(uuid.uuid4())
                entry = GrammarConcept(
                    id=entry_id,
                    slug=key,
                    name=name,
                    explanation=raw_grammar.get("explanation", ""),
                    examples=examples,
                    first_seen_unit=unit_num,
                    units_encountered=[unit_num],
                )
                grammar_index[key] = entry
                new_ids.append(entry_id)

        unit_grammar[unit_num] = (new_ids, review_ids)

    return list(grammar_index.values()), unit_grammar


def create_unit_views(
    extractions: dict[int, dict],
    unit_vocab: dict[int, tuple[list[str], list[str]]],
    unit_grammar: dict[int, tuple[list[str], list[str]]],
) -> list[UnitView]:
    """Create per-unit view objects."""
    views = []
    for unit_num in sorted(extractions.keys()):
        new_vocab_ids, review_vocab_ids = unit_vocab.get(unit_num, ([], []))
        new_concept_ids, review_concept_ids = unit_grammar.get(unit_num, ([], []))

        view = UnitView(
            unit_number=unit_num,
            title=f"Unit {unit_num}",  # Could extract from textbook
            new_vocabulary_ids=new_vocab_ids,
            new_concept_ids=new_concept_ids,
            review_vocabulary_ids=list(set(review_vocab_ids)),  # Dedupe
            review_concept_ids=list(set(review_concept_ids)),
        )
        views.append(view)
    return views


def create_index(
    vocabulary: list[VocabularyEntry],
    concepts: list[GrammarConcept],
    unit_views: list[UnitView],
) -> ExtractedIndex:
    """Create index with summary stats."""
    summaries = []
    for view in unit_views:
        summaries.append(UnitSummary(
            unit_number=view.unit_number,
            title=view.title,
            new_vocab_count=len(view.new_vocabulary_ids),
            review_vocab_count=len(view.review_vocabulary_ids),
            new_concept_count=len(view.new_concept_ids),
            review_concept_count=len(view.review_concept_ids),
            exercise_count=len(view.exercises),
        ))

    total_examples = sum(len(v.examples) for v in vocabulary) + sum(len(c.examples) for c in concepts)

    return ExtractedIndex(
        units=summaries,
        total_vocab=len(vocabulary),
        total_concepts=len(concepts),
        total_examples=total_examples,
        extraction_date=datetime.now().isoformat(),
    )


def save_outputs(
    output_dir: Path,
    vocabulary: list[VocabularyEntry],
    concepts: list[GrammarConcept],
    unit_views: list[UnitView],
    index: ExtractedIndex,
):
    """Save all output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # vocabulary.json
    vocab_path = output_dir / "vocabulary.json"
    with open(vocab_path, "w") as f:
        json.dump([v.model_dump() for v in vocabulary], f, ensure_ascii=False, indent=2)
    print(f"  Saved {vocab_path}")

    # grammar.json
    grammar_path = output_dir / "grammar.json"
    with open(grammar_path, "w") as f:
        json.dump([c.model_dump() for c in concepts], f, ensure_ascii=False, indent=2)
    print(f"  Saved {grammar_path}")

    # units/*.json
    units_dir = output_dir / "units"
    units_dir.mkdir(exist_ok=True)
    for view in unit_views:
        unit_path = units_dir / f"{view.unit_number:02d}.json"
        with open(unit_path, "w") as f:
            json.dump(view.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(unit_views)} unit views to {units_dir}/")

    # index.json
    index_path = output_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"  Saved {index_path}")


def print_stats(vocabulary: list[VocabularyEntry], concepts: list[GrammarConcept]):
    """Print merge statistics."""
    print("\n" + "=" * 60)
    print("MERGE STATISTICS")
    print("=" * 60)

    print(f"\nTotal canonical vocabulary: {len(vocabulary)}")
    print(f"Total grammar concepts: {len(concepts)}")

    # Vocab by POS
    pos_counts = {}
    for v in vocabulary:
        pos_counts[v.part_of_speech.value] = pos_counts.get(v.part_of_speech.value, 0) + 1
    print("\nVocabulary by part of speech:")
    for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1]):
        print(f"  {pos}: {count}")

    # Multi-unit vocab
    multi_unit = [v for v in vocabulary if len(v.units_encountered) > 1]
    print(f"\nVocabulary appearing in multiple units: {len(multi_unit)}")
    if multi_unit[:5]:
        print("  Examples:")
        for v in multi_unit[:5]:
            print(f"    {v.hindi} ({v.transliteration}): units {v.units_encountered}")

    # Example counts
    total_vocab_examples = sum(len(v.examples) for v in vocabulary)
    total_grammar_examples = sum(len(c.examples) for c in concepts)
    print(f"\nTotal examples: {total_vocab_examples + total_grammar_examples}")
    print(f"  Vocabulary examples: {total_vocab_examples}")
    print(f"  Grammar examples: {total_grammar_examples}")


def main():
    print("=" * 60)
    print("Hindi Extraction (Phase 2 - Merge)")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent / "study-materials" / "extracted"
    raw_dir = base_dir / "raw"

    if not raw_dir.exists():
        print(f"\nError: Raw extractions not found at {raw_dir}")
        print("Run test_extraction.py --all first")
        return

    # Load raw extractions
    print("\nLoading raw extractions...")
    extractions = load_raw_extractions(raw_dir)

    if not extractions:
        print("No valid extractions found")
        return

    # Merge vocabulary
    print("\nMerging vocabulary (earliest unit owns, examples aggregated)...")
    vocabulary, unit_vocab = merge_vocabulary(extractions)

    # Merge grammar
    print("\nMerging grammar concepts...")
    concepts, unit_grammar = merge_grammar(extractions)

    # Create unit views
    print("\nCreating per-unit views...")
    unit_views = create_unit_views(extractions, unit_vocab, unit_grammar)

    # Create index
    index = create_index(vocabulary, concepts, unit_views)

    # Save outputs
    print("\nSaving outputs...")
    save_outputs(base_dir, vocabulary, concepts, unit_views, index)

    # Print stats
    print_stats(vocabulary, concepts)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"\nOutput directory: {base_dir}")
    print("Files created:")
    print("  - vocabulary.json (canonical vocab for Anki)")
    print("  - grammar.json (grammar concepts)")
    print("  - units/*.json (per-unit views)")
    print("  - index.json (summary)")


if __name__ == "__main__":
    main()
