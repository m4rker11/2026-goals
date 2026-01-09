#!/usr/bin/env python3
"""
Phase 1: Raw extraction from Hindi textbook chapters.

Extracts vocabulary and grammar with CANONICAL forms for later deduplication.
Outputs to study-materials/extracted/raw/*.json

Usage:
    python scripts/test_extraction.py [model_name] [--all] [--unit N]

    Examples:
        python scripts/test_extraction.py gemini-3-flash-preview
        python scripts/test_extraction.py gemini-3-flash-preview --all
        python scripts/test_extraction.py gemini-3-flash-preview --unit 5

Models:
    - gemini-3-flash-preview (Google, via gemini CLI)
    - gpt-oss-20b (OpenAI, ~12GB, LM Studio)
    - nemotron-3-nano-30b-a3b (NVIDIA, ~18GB Q4, LM Studio)

Requirements:
    - gemini CLI installed
    - pip install instructor openai pydantic
"""

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import instructor
from pydantic import BaseModel, Field


# Chunk settings
CHUNK_SIZE = 3000  # chars per chunk
CHUNK_OVERLAP = 300  # overlap between chunks
MAX_PARALLEL_UNITS = 3  # process 3 units in parallel


# =============================================================================
# EXTRACTION MODELS (matches hindi_schemas.py RawChunkExtract)
# =============================================================================

class Example(BaseModel):
    hindi: str
    transliteration: str
    english: str


class RawVocabEntry(BaseModel):
    """Vocabulary with canonical form for deduplication."""
    # Canonical/dictionary form (for deduplication)
    hindi: str = Field(description="Canonical form: infinitive for verbs, singular direct for nouns")
    transliteration: str = Field(description="Transliteration of canonical form")
    meaning: str
    part_of_speech: str = Field(description="noun, verb, adj, adv, postposition, pronoun, etc.")

    # Form as encountered (if different from canonical)
    encountered_form: str | None = Field(None, description="The inflected form in text, if different from canonical")
    encountered_translit: str | None = None

    # Noun-specific
    gender: str | None = Field(None, description="'m' or 'f' for nouns only")

    # Examples from this chunk
    examples: list[Example] = Field(default_factory=list)


class RawGrammarPoint(BaseModel):
    name: str
    explanation: str
    examples: list[Example] = Field(default_factory=list)


class RawChunkExtract(BaseModel):
    """Extraction result from a single chunk."""
    vocabulary: list[RawVocabEntry] = Field(default_factory=list)
    grammar_points: list[RawGrammarPoint] = Field(default_factory=list)


# =============================================================================
# HELPERS
# =============================================================================

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks with overlap."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def extract_json_from_response(text: str) -> str:
    """Extract JSON from markdown code blocks if present."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


def merge_chunk_extractions(extractions: list[RawChunkExtract]) -> RawChunkExtract:
    """Merge multiple chunk extractions, deduplicating by (canonical hindi, POS)."""
    seen_vocab: dict[tuple[str, str], RawVocabEntry] = {}
    seen_grammar: dict[str, RawGrammarPoint] = {}

    for ext in extractions:
        for v in ext.vocabulary:
            key = (v.hindi, v.part_of_speech)
            if key in seen_vocab:
                # Aggregate examples
                seen_vocab[key].examples.extend(v.examples)
            else:
                seen_vocab[key] = v

        for g in ext.grammar_points:
            if g.name not in seen_grammar:
                seen_grammar[g.name] = g
            else:
                # Aggregate examples
                seen_grammar[g.name].examples.extend(g.examples)

    return RawChunkExtract(
        vocabulary=list(seen_vocab.values()),
        grammar_points=list(seen_grammar.values())
    )


def call_gemini_cli(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call gemini CLI and return the response."""
    result = subprocess.run(
        ["gemini", "-m", model, "-o", "json"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI error: {result.stderr}")

    output = json.loads(result.stdout)
    return output.get("response", "")


def get_client(model_name: str):
    """Get appropriate client based on model name."""
    if "gemini" in model_name.lower():
        return None, "gemini-cli"
    else:
        from openai import OpenAI
        return instructor.from_openai(
            OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio"),
            mode=instructor.Mode.JSON,
        ), "lmstudio"


# =============================================================================
# EXTRACTION
# =============================================================================

EXTRACTION_PROMPT = """You are extracting structured data from a Hindi language textbook.

CRITICAL REQUIREMENTS:
1. Provide transliteration (Roman script) for ALL Hindi text - the user cannot read Devanagari
2. Use CANONICAL/DICTIONARY forms for vocabulary (see rules below)

Return ONLY valid JSON matching this schema:
{schema}

=== CANONICALIZATION RULES ===

For the "hindi" and "transliteration" fields, always use the CANONICAL (dictionary) form:

| Type | Rule | Example |
|------|------|---------|
| Nouns | Singular direct case | लड़के/लड़कों → लड़का (laṛkā) |
| Adjectives | Masculine singular | अच्छी/अच्छे → अच्छा (acchā) |
| Verbs | Infinitive | करता/करती/किया → करना (karnā) |
| Postpositions | Masculine form | की/के → का (kā) |

If the text has an inflected form (like लड़के), put the CANONICAL form (लड़का) in "hindi"
and put the encountered form (लड़के) in "encountered_form".

=== EXTRACTION INSTRUCTIONS ===

1. VOCABULARY - Extract ALL words with:
   - hindi: CANONICAL form (infinitive/singular/masculine base)
   - transliteration: Transliteration of canonical form
   - meaning: English translation
   - part_of_speech: noun, verb, adj, adv, postposition, pronoun, conjunction, particle
   - gender: "m" or "f" for nouns ONLY, null for others
   - encountered_form: The form in text if different from canonical (optional)
   - examples: 1-2 example sentences showing usage

2. GRAMMAR POINTS - Extract concepts with:
   - name: Name of the grammar concept
   - explanation: Clear 2-3 sentence explanation
   - examples: Hindi examples WITH transliteration and English translation

=== TEXT TO EXTRACT ===

{text}
"""


def extract_chunk(chunk: str, model_name: str, client, client_type: str) -> RawChunkExtract:
    """Extract from a single chunk of text."""
    schema = RawChunkExtract.model_json_schema()
    prompt = EXTRACTION_PROMPT.format(
        schema=json.dumps(schema, indent=2),
        text=chunk
    )

    if client_type == "gemini-cli":
        response_text = call_gemini_cli(prompt, model_name)
        json_str = extract_json_from_response(response_text)
        return RawChunkExtract.model_validate_json(json_str)
    else:
        return client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_model=RawChunkExtract,
            max_tokens=4096,
        )


def extract_unit(unit_num: int, model_name: str, verbose: bool = True) -> dict:
    """Extract a single unit. Returns dict with result or error."""
    start = time.time()
    try:
        chapter_text = load_chapter(unit_num)
        client, client_type = get_client(model_name)
        chunks = chunk_text(chapter_text)

        if verbose:
            print(f"  Unit {unit_num}: {len(chapter_text)} chars, {len(chunks)} chunks")

        extractions = []
        for i, chunk in enumerate(chunks):
            try:
                result = extract_chunk(chunk, model_name, client, client_type)
                extractions.append(result)
                if verbose:
                    print(f"    Chunk {i+1}/{len(chunks)}: {len(result.vocabulary)} vocab, {len(result.grammar_points)} grammar")
            except Exception as e:
                if verbose:
                    print(f"    Chunk {i+1}/{len(chunks)}: FAILED - {e}")
                continue

        if not extractions:
            raise RuntimeError("All chunks failed")

        merged = merge_chunk_extractions(extractions)
        elapsed = time.time() - start

        return {
            "unit_number": unit_num,
            "vocabulary": [v.model_dump() for v in merged.vocabulary],
            "grammar_points": [g.model_dump() for g in merged.grammar_points],
            "stats": {
                "vocab_count": len(merged.vocabulary),
                "grammar_count": len(merged.grammar_points),
                "chunks_processed": len(extractions),
                "chunks_total": len(chunks),
                "elapsed_seconds": elapsed,
            }
        }

    except Exception as e:
        return {
            "unit_number": unit_num,
            "error": str(e),
            "stats": {"elapsed_seconds": time.time() - start}
        }


def extract_all_units(model_name: str, units: list[int] | None = None) -> dict:
    """Extract multiple units in parallel (3 at a time)."""
    if units is None:
        units = list(range(1, 19))  # Units 1-18

    results = {}
    print(f"\nExtracting {len(units)} units with {MAX_PARALLEL_UNITS} parallel workers...")

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_UNITS) as executor:
        futures = {executor.submit(extract_unit, u, model_name, verbose=False): u for u in units}

        for future in as_completed(futures):
            result = future.result()
            unit_num = result["unit_number"]
            if "error" in result:
                print(f"  Unit {unit_num}: FAILED - {result['error']}")
            else:
                stats = result["stats"]
                print(f"  Unit {unit_num}: {stats['vocab_count']} vocab, {stats['grammar_count']} grammar ({stats['elapsed_seconds']:.1f}s)")
            results[unit_num] = result

    return results


def load_chapter(unit_num: int) -> str:
    """Load a chapter from the textbook."""
    textbook_dir = Path(__file__).parent.parent / "study-materials" / "textbook"
    chapter_file = textbook_dir / f"{unit_num:02d}_unit_{unit_num}.md"

    if not chapter_file.exists():
        raise FileNotFoundError(f"Chapter not found: {chapter_file}")

    return chapter_file.read_text()


def save_raw_extraction(result: dict, model_name: str, output_dir: Path):
    """Save a single unit's raw extraction."""
    output_dir.mkdir(parents=True, exist_ok=True)
    unit_num = result["unit_number"]
    output_path = output_dir / f"{unit_num:02d}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return output_path


# =============================================================================
# DISPLAY
# =============================================================================

def print_sample(result: dict, n: int = 5):
    """Print sample of extracted content."""
    vocab = result.get("vocabulary", [])
    grammar = result.get("grammar_points", [])

    print("\n=== SAMPLE VOCABULARY ===")
    for v in vocab[:n]:
        gender = f" ({v['gender']})" if v.get('gender') else ""
        encountered = f" [text: {v['encountered_form']}]" if v.get('encountered_form') else ""
        print(f"  {v['hindi']} → {v['transliteration']} = {v['meaning']}{gender} [{v['part_of_speech']}]{encountered}")

    print("\n=== SAMPLE GRAMMAR ===")
    for g in grammar[:2]:
        print(f"\n  {g['name']}")
        explanation = g['explanation'][:200] + "..." if len(g['explanation']) > 200 else g['explanation']
        print(f"  {explanation}")
        if g.get('examples'):
            ex = g['examples'][0]
            print(f"  Example: {ex['hindi']} ({ex['transliteration']}) = {ex['english']}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    import sys

    # Parse args
    args = sys.argv[1:]
    extract_all = "--all" in args
    unit_arg = None
    for i, a in enumerate(args):
        if a == "--unit" and i + 1 < len(args):
            unit_arg = int(args[i + 1])
    args = [a for a in args if not a.startswith("--") and not a.isdigit()]
    model_name = args[0] if args else "gemini-3-flash-preview"

    print("=" * 60)
    print(f"Hindi Extraction (Phase 1 - Raw)")
    print("=" * 60)
    print(f"\nModel: {model_name}")
    if "gemini" in model_name.lower():
        print("Backend: Gemini CLI")
    else:
        print("Backend: LM Studio (http://localhost:1234/v1)")

    # Output directory
    output_dir = Path(__file__).parent.parent / "study-materials" / "extracted" / "raw"

    if extract_all:
        # Extract all units
        results = extract_all_units(model_name)

        # Save each unit
        for unit_num, result in sorted(results.items()):
            if "error" not in result:
                save_raw_extraction(result, model_name, output_dir)

        # Calculate totals
        total_vocab = sum(r.get("stats", {}).get("vocab_count", 0) for r in results.values() if "stats" in r)
        total_grammar = sum(r.get("stats", {}).get("grammar_count", 0) for r in results.values() if "stats" in r)
        total_time = sum(r.get("stats", {}).get("elapsed_seconds", 0) for r in results.values())
        failed = sum(1 for r in results.values() if "error" in r)

        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print("=" * 60)
        print(f"Units processed: {len(results) - failed}/{len(results)}")
        print(f"Total vocabulary: {total_vocab}")
        print(f"Total grammar points: {total_grammar}")
        print(f"Total time: {total_time:.1f}s")
        print(f"\nRaw extractions saved to: {output_dir}/")
        print("\nNext step: Run merge_extractions.py to deduplicate across units")

    else:
        # Single unit test
        test_unit = unit_arg or 3
        print(f"\nMode: Single unit test (Unit {test_unit})")
        print()

        result = extract_unit(test_unit, model_name, verbose=True)

        if "error" in result:
            print(f"\nExtraction failed: {result['error']}")
            return

        stats = result["stats"]
        print(f"\n{'=' * 60}")
        print(f"RESULTS: Unit {test_unit}")
        print("=" * 60)
        print(f"Time: {stats['elapsed_seconds']:.1f}s")
        print(f"Chunks: {stats['chunks_processed']}/{stats['chunks_total']}")
        print(f"Vocabulary: {stats['vocab_count']}")
        print(f"Grammar points: {stats['grammar_count']}")

        print_sample(result)

        # Save
        output_path = save_raw_extraction(result, model_name, output_dir)
        print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
