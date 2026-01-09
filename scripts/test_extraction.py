#!/usr/bin/env python3
"""
Phase 1: Extract complete learning content from Hindi textbook.

Extracts:
- Dialogues (speaker turns with Hindi/translit/English)
- Grammar sections (rules, patterns, examples, tables)
- Exercises (comprehension, translation, writing)
- Vocabulary (canonical forms)

Usage:
    python scripts/test_extraction.py [model_name] [--all] [--unit N]
"""

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import instructor
from pydantic import BaseModel, Field


# Chunk settings - smaller to avoid JSON truncation
CHUNK_SIZE = 2500
CHUNK_OVERLAP = 300
RETRY_CHUNK_SIZE = 1500  # Even smaller for retries
MAX_PARALLEL_UNITS = 3

# Overlap markers for extraction
MARKER_CONTEXT_ONLY = "<<CONTEXT_ONLY>>"
MARKER_EXTRACT_FROM = "<<EXTRACT_FROM_HERE>>"
MARKER_END_EXTRACT = "<<END_EXTRACT>>"


# =============================================================================
# EXTRACTION MODELS
# =============================================================================

class DialogueTurn(BaseModel):
    speaker: str
    hindi: str
    transliteration: str
    english: str


class Dialogue(BaseModel):
    section_id: str = Field(description="e.g., '3a', '3b'")
    title: str
    turns: list[DialogueTurn]
    context: str | None = None


class GrammarExample(BaseModel):
    hindi: str
    transliteration: str
    english: str
    notes: str | None = None


class GrammarRule(BaseModel):
    rule: str = Field(description="The grammar rule statement")
    pattern: str | None = Field(None, description="Pattern like 'X + में = in X'")
    examples: list[GrammarExample] = Field(default_factory=list)


class GrammarSection(BaseModel):
    section_id: str = Field(description="e.g., '3.1', '3.2'")
    title: str
    explanation: str
    rules: list[GrammarRule] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list, description="Key takeaways")


class ExerciseItem(BaseModel):
    number: str
    prompt_hindi: str | None = None
    prompt_translit: str | None = None
    prompt_english: str | None = None
    answer_hindi: str | None = None
    answer_translit: str | None = None
    answer_english: str | None = None


class Exercise(BaseModel):
    exercise_id: str = Field(description="e.g., '3a.1', '3b.2'")
    instruction: str
    exercise_type: str = Field(description="comprehension, translation, writing")
    items: list[ExerciseItem] = Field(default_factory=list)
    based_on: str | None = Field(None, description="Reference like 'Dialogue 3a'")


class VocabEntry(BaseModel):
    hindi: str = Field(description="Canonical form")
    transliteration: str
    meaning: str
    part_of_speech: str
    gender: str | None = Field(None, description="'m' or 'f' for nouns")
    encountered_form: str | None = Field(None, description="Inflected form if different")


class ChunkExtract(BaseModel):
    """Partial extraction from one chunk."""
    dialogues: list[Dialogue] = Field(default_factory=list)
    grammar_sections: list[GrammarSection] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)
    vocabulary: list[VocabEntry] = Field(default_factory=list)


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


def chunk_text_with_markers(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks with overlap markers.

    Markers tell Gemini:
    - <<CONTEXT_ONLY>>: Previous chunk's content, for context only
    - <<EXTRACT_FROM_HERE>>: Start extracting new content here
    - <<END_EXTRACT>>: Stop extracting, complete current section then stop
    """
    if len(text) <= chunk_size:
        return [text]

    # Calculate chunk boundaries
    boundaries = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        boundaries.append((start, end))
        if end >= len(text):
            break
        start = end - overlap

    # Build chunks with markers
    marked_chunks = []
    for i, (start, end) in enumerate(boundaries):
        is_first = i == 0
        is_last = i == len(boundaries) - 1

        if is_first:
            # First chunk: no context prefix, add end marker before overlap
            if is_last:
                chunk = text[start:end]
            else:
                extract_end = end - overlap
                chunk = text[start:extract_end] + f"\n{MARKER_END_EXTRACT}\n" + text[extract_end:end]
        elif is_last:
            # Last chunk: context prefix, extract marker, no end marker
            context_end = start + overlap
            chunk = (
                f"{MARKER_CONTEXT_ONLY}\n" + text[start:context_end] +
                f"\n{MARKER_EXTRACT_FROM}\n" + text[context_end:end]
            )
        else:
            # Middle chunk: context prefix, extract marker, end marker
            context_end = start + overlap
            extract_end = end - overlap
            chunk = (
                f"{MARKER_CONTEXT_ONLY}\n" + text[start:context_end] +
                f"\n{MARKER_EXTRACT_FROM}\n" + text[context_end:extract_end] +
                f"\n{MARKER_END_EXTRACT}\n" + text[extract_end:end]
            )

        marked_chunks.append(chunk)

    return marked_chunks


def chunk_by_sections(text: str, max_chunk_size: int = 5000) -> list[str]:
    """Split text at section boundaries (3a, 3.1, etc.) to avoid breaking dialogues."""
    import re

    # Find section markers: "3a ", "3.1 ", "3b ", "EXERCISE", "Grammar", etc.
    section_pattern = r'\n(?=(?:\d+[a-z]?\s+[A-Z]|\d+\.\d+\s+[A-Z]|EXERCISE|Grammar|QUICK VOCAB))'

    # Split at section boundaries
    parts = re.split(section_pattern, text)

    # Combine small parts, split large ones
    chunks = []
    current = ""

    for part in parts:
        if len(current) + len(part) <= max_chunk_size:
            current += part
        else:
            if current:
                chunks.append(current)
            # If single part is too large, fall back to chunking with markers
            if len(part) > max_chunk_size:
                chunks.extend(chunk_text_with_markers(part, max_chunk_size, 200))
            else:
                current = part

    if current:
        chunks.append(current)

    return chunks if chunks else [text]


def extract_json_from_response(text: str) -> str:
    """Extract JSON from markdown code blocks if present."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


def normalize_hindi(text: str) -> str:
    """Normalize Hindi text for comparison - use first 15 chars after removing punctuation."""
    import re
    # Remove punctuation and spaces
    text = re.sub(r'[।?.!,;:\s]', '', text.strip())
    # Use first 15 chars as signature (catches paraphrases with same start)
    return text[:15]


def normalize_speaker_for_dedup(turns: list[DialogueTurn]) -> dict[str, str]:
    """Create a mapping from raw speaker names to normalized labels (A, B, C...).

    Groups similar names together (same first few chars after normalization).
    """
    import re

    def simplify(name: str) -> str:
        """Reduce name to first 4 alphanumeric chars, lowercase."""
        # Remove diacritics-ish by keeping only basic chars
        simple = re.sub(r'[^a-zA-Z\u0900-\u097F]', '', name.strip().lower())
        return simple[:4] if simple else name[:4].lower()

    # Group speakers by simplified name
    simplified_to_raw = {}
    for turn in turns:
        simp = simplify(turn.speaker)
        if simp not in simplified_to_raw:
            simplified_to_raw[simp] = turn.speaker

    # Assign labels A, B, C... in order of first appearance
    labels = {}
    label_idx = 0
    for turn in turns:
        simp = simplify(turn.speaker)
        if simp not in labels:
            labels[simp] = chr(ord('A') + label_idx)
            label_idx += 1

    # Map raw names to labels
    raw_to_label = {}
    for turn in turns:
        simp = simplify(turn.speaker)
        raw_to_label[turn.speaker] = labels[simp]

    return raw_to_label


def dedupe_dialogue_turns(turns: list[DialogueTurn]) -> list[DialogueTurn]:
    """Remove duplicate turns using normalized Hindi text only.

    Speaker names vary across chunks (Prakash vs प्रकाश) but the Hindi
    dialogue line itself is unique within a section.
    """
    if not turns:
        return turns

    seen = set()
    result = []
    for turn in turns:
        # Use only Hindi text as key - same line won't appear twice in a dialogue
        key = normalize_hindi(turn.hindi)
        if key not in seen:
            seen.add(key)
            result.append(turn)

    return result


def merge_chunk_extracts(extracts: list[ChunkExtract]) -> ChunkExtract:
    """Merge multiple chunk extractions."""
    seen_dialogues = {}
    seen_grammar = {}
    seen_exercises = {}
    seen_vocab = {}

    for ext in extracts:
        for d in ext.dialogues:
            if d.section_id not in seen_dialogues:
                seen_dialogues[d.section_id] = d
            else:
                # Append turns - we'll dedupe later
                seen_dialogues[d.section_id].turns.extend(d.turns)

        for g in ext.grammar_sections:
            if g.section_id not in seen_grammar:
                seen_grammar[g.section_id] = g
            else:
                # Merge rules
                existing = seen_grammar[g.section_id]
                existing_rules = {r.rule for r in existing.rules}
                for rule in g.rules:
                    if rule.rule not in existing_rules:
                        existing.rules.append(rule)

        for e in ext.exercises:
            if e.exercise_id not in seen_exercises:
                seen_exercises[e.exercise_id] = e

        for v in ext.vocabulary:
            key = (v.hindi, v.part_of_speech)
            if key not in seen_vocab:
                seen_vocab[key] = v

    # Dedupe turns in each dialogue
    for dlg in seen_dialogues.values():
        dlg.turns = dedupe_dialogue_turns(dlg.turns)

    return ChunkExtract(
        dialogues=list(seen_dialogues.values()),
        grammar_sections=list(seen_grammar.values()),
        exercises=list(seen_exercises.values()),
        vocabulary=list(seen_vocab.values()),
    )


def call_gemini_cli(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call gemini CLI and return the response."""
    result = subprocess.run(
        ["gemini", "-m", model, "-o", "json"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI error: {result.stderr}")

    output = json.loads(result.stdout)
    return output.get("response", "")


def get_client(model_name: str):
    if "gemini" in model_name.lower():
        return None, "gemini-cli"
    else:
        from openai import OpenAI
        return instructor.from_openai(
            OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio"),
            mode=instructor.Mode.JSON,
        ), "lmstudio"


# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

EXTRACTION_PROMPT = """You are extracting structured learning content from a Hindi language textbook.

CRITICAL: Provide transliteration (Roman script) for ALL Hindi text. The user cannot read Devanagari.

Return ONLY valid JSON matching this schema:
{schema}

=== EXTRACTION INSTRUCTIONS ===

**1. DIALOGUES** (sections like "3a", "3b")
Extract complete conversations with:
- section_id: "3a", "3b", etc.
- title: The dialogue title
- turns: Each speaker turn with hindi, transliteration, english
- context: Brief description of situation

IMPORTANT: The source text shows dialogues in multiple formats (Devanagari, then transliteration, then English).
Extract each turn ONLY ONCE - use the Devanagari version as the hindi field, provide your own transliteration,
and use the English translation. Do NOT create duplicate turns from the transliterated or English versions.

**2. GRAMMAR SECTIONS** (sections like "3.1", "3.2")
Extract grammar explanations with:
- section_id: "3.1", "3.2", etc.
- title: "Simple postpositions", "Oblique case", etc.
- explanation: Main explanation text (2-4 sentences)
- rules: Specific rules with patterns and examples
  - rule: Statement of the rule
  - pattern: Formula like "Noun + में = in the noun"
  - examples: Hindi/translit/english examples
- key_points: Bullet points to remember

**3. EXERCISES** (sections like "3a.1", "3b.2")
Extract practice exercises:
- exercise_id: "3a.1", "3b.2"
- instruction: "Translate these sentences", "Answer questions", etc.
- exercise_type: "comprehension", "translation", "writing"
- items: Each question with prompt and answer (if given)
- based_on: Reference like "Dialogue 3a" for comprehension

**4. VOCABULARY**
Extract all vocabulary with CANONICAL forms:
- hindi: Dictionary form (infinitive for verbs, singular for nouns)
- transliteration: Romanization
- meaning: English
- part_of_speech: noun, verb, adj, postposition, etc.
- gender: "m" or "f" for nouns
- encountered_form: The form in text if different from canonical

Canonicalization rules:
- Nouns: singular direct (लड़के → लड़का)
- Adjectives: masculine singular (अच्छी → अच्छा)
- Verbs: infinitive (करता → करना)

=== CHUNK BOUNDARY MARKERS ===

The text may contain these markers to indicate extraction boundaries:

**<<CONTEXT_ONLY>>** - Content after this is from the previous chunk, provided for context only.
Do NOT extract content from this section (it was already extracted in the previous chunk).

**<<EXTRACT_FROM_HERE>>** - Start extracting content from this point onwards.

**<<END_EXTRACT>>** - Stop extracting NEW content after this marker.
IMPORTANT: If you are in the middle of extracting a section (dialogue, grammar, exercise),
COMPLETE that section first, then stop. Do NOT start any new sections after this marker.
Content after <<END_EXTRACT>> is context for the next chunk.

If no markers are present, extract the entire text.

=== TEXT TO EXTRACT ===

{text}
"""


def extract_chunk(chunk: str, model_name: str, client, client_type: str) -> ChunkExtract:
    """Extract from a single chunk."""
    schema = ChunkExtract.model_json_schema()
    prompt = EXTRACTION_PROMPT.format(
        schema=json.dumps(schema, indent=2),
        text=chunk
    )

    if client_type == "gemini-cli":
        response_text = call_gemini_cli(prompt, model_name)
        json_str = extract_json_from_response(response_text)
        return ChunkExtract.model_validate_json(json_str)
    else:
        return client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_model=ChunkExtract,
            max_tokens=8192,
        )


def extract_chunk_with_retry(chunk: str, model_name: str, client, client_type: str, verbose: bool = False) -> ChunkExtract | None:
    """Extract with retry on smaller chunks if needed."""
    try:
        return extract_chunk(chunk, model_name, client, client_type)
    except Exception as e:
        if "EOF" in str(e) or "Invalid JSON" in str(e):
            # JSON truncation - try smaller sub-chunks
            if len(chunk) > RETRY_CHUNK_SIZE:
                if verbose:
                    print(f" (retrying as sub-chunks)")
                sub_chunks = chunk_text_with_markers(chunk, RETRY_CHUNK_SIZE, 150)
                sub_extracts = []
                for sc in sub_chunks:
                    try:
                        result = extract_chunk(sc, model_name, client, client_type)
                        sub_extracts.append(result)
                    except:
                        continue
                if sub_extracts:
                    return merge_chunk_extracts(sub_extracts)
        raise


def extract_unit(unit_num: int, model_name: str, verbose: bool = True) -> dict:
    """Extract a single unit."""
    start = time.time()
    try:
        chapter_text = load_chapter(unit_num)
        client, client_type = get_client(model_name)

        # Use section-aware chunking to avoid breaking dialogues
        chunks = chunk_by_sections(chapter_text, max_chunk_size=4000)

        if verbose:
            print(f"  Unit {unit_num}: {len(chapter_text)} chars, {len(chunks)} section-chunks")

        extracts = []
        for i, chunk in enumerate(chunks):
            try:
                if verbose:
                    print(f"    Chunk {i+1}/{len(chunks)}...", end=" ", flush=True)
                result = extract_chunk_with_retry(chunk, model_name, client, client_type, verbose)
                extracts.append(result)
                if verbose:
                    print(f"{len(result.dialogues)} dlg, {len(result.grammar_sections)} gram, "
                          f"{len(result.exercises)} ex, {len(result.vocabulary)} vocab")
            except Exception as e:
                if verbose:
                    print(f"FAILED - {str(e)[:50]}")
                continue

        if not extracts:
            raise RuntimeError("All chunks failed")

        merged = merge_chunk_extracts(extracts)
        elapsed = time.time() - start

        return {
            "unit_number": unit_num,
            "dialogues": [d.model_dump() for d in merged.dialogues],
            "grammar_sections": [g.model_dump() for g in merged.grammar_sections],
            "exercises": [e.model_dump() for e in merged.exercises],
            "vocabulary": [v.model_dump() for v in merged.vocabulary],
            "stats": {
                "dialogue_count": len(merged.dialogues),
                "grammar_section_count": len(merged.grammar_sections),
                "exercise_count": len(merged.exercises),
                "vocab_count": len(merged.vocabulary),
                "chunks_processed": len(extracts),
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
    """Extract multiple units in parallel."""
    if units is None:
        units = list(range(1, 19))

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
                s = result["stats"]
                print(f"  Unit {unit_num}: {s['dialogue_count']} dlg, {s['grammar_section_count']} gram, "
                      f"{s['exercise_count']} ex, {s['vocab_count']} vocab ({s['elapsed_seconds']:.1f}s)")
            results[unit_num] = result

    return results


def load_chapter(unit_num: int) -> str:
    """Load a chapter from the textbook."""
    textbook_dir = Path(__file__).parent.parent / "study-materials" / "textbook"
    chapter_file = textbook_dir / f"{unit_num:02d}_unit_{unit_num}.md"

    if not chapter_file.exists():
        raise FileNotFoundError(f"Chapter not found: {chapter_file}")

    return chapter_file.read_text()


def save_extraction(result: dict, output_dir: Path):
    """Save extraction result."""
    output_dir.mkdir(parents=True, exist_ok=True)
    unit_num = result["unit_number"]
    output_path = output_dir / f"{unit_num:02d}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return output_path


# =============================================================================
# DISPLAY
# =============================================================================

def print_sample(result: dict):
    """Print sample of extracted content."""
    print("\n=== DIALOGUES ===")
    for d in result.get("dialogues", [])[:1]:
        print(f"\n  [{d['section_id']}] {d['title']}")
        for turn in d.get("turns", [])[:3]:
            print(f"    {turn['speaker']}: {turn['hindi']}")
            print(f"      ({turn['transliteration']})")
            print(f"      {turn['english']}")

    print("\n=== GRAMMAR ===")
    for g in result.get("grammar_sections", [])[:2]:
        print(f"\n  [{g['section_id']}] {g['title']}")
        exp = g.get('explanation', '')[:150]
        print(f"    {exp}...")
        for rule in g.get("rules", [])[:1]:
            print(f"    Rule: {rule['rule'][:80]}...")
            if rule.get("pattern"):
                print(f"    Pattern: {rule['pattern']}")

    print("\n=== EXERCISES ===")
    for e in result.get("exercises", [])[:2]:
        print(f"\n  [{e['exercise_id']}] {e['exercise_type']}: {e['instruction'][:50]}...")
        print(f"    {len(e.get('items', []))} items")

    print("\n=== VOCABULARY (sample) ===")
    for v in result.get("vocabulary", [])[:5]:
        gender = f" ({v['gender']})" if v.get('gender') else ""
        print(f"  {v['hindi']} → {v['transliteration']} = {v['meaning']}{gender} [{v['part_of_speech']}]")


# =============================================================================
# MAIN
# =============================================================================

def main():
    import sys

    args = sys.argv[1:]
    extract_all = "--all" in args
    unit_arg = None
    for i, a in enumerate(args):
        if a == "--unit" and i + 1 < len(args):
            unit_arg = int(args[i + 1])
    args = [a for a in args if not a.startswith("--") and not a.isdigit()]
    model_name = args[0] if args else "gemini-3-flash-preview"

    print("=" * 60)
    print("Hindi Textbook Extraction")
    print("=" * 60)
    print(f"\nModel: {model_name}")
    print("Backend:", "Gemini CLI" if "gemini" in model_name.lower() else "LM Studio")

    output_dir = Path(__file__).parent.parent / "study-materials" / "extracted" / "raw"

    if extract_all:
        results = extract_all_units(model_name)

        for unit_num, result in sorted(results.items()):
            if "error" not in result:
                save_extraction(result, output_dir)

        # Summary
        successful = [r for r in results.values() if "error" not in r]
        total_dlg = sum(r["stats"]["dialogue_count"] for r in successful)
        total_gram = sum(r["stats"]["grammar_section_count"] for r in successful)
        total_ex = sum(r["stats"]["exercise_count"] for r in successful)
        total_vocab = sum(r["stats"]["vocab_count"] for r in successful)
        total_time = sum(r["stats"]["elapsed_seconds"] for r in successful)

        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print("=" * 60)
        print(f"Units: {len(successful)}/{len(results)}")
        print(f"Dialogues: {total_dlg}")
        print(f"Grammar sections: {total_gram}")
        print(f"Exercises: {total_ex}")
        print(f"Vocabulary: {total_vocab}")
        print(f"Time: {total_time:.1f}s")
        print(f"\nSaved to: {output_dir}/")

    else:
        test_unit = unit_arg or 3
        print(f"\nMode: Single unit (Unit {test_unit})")

        result = extract_unit(test_unit, model_name, verbose=True)

        if "error" in result:
            print(f"\nFailed: {result['error']}")
            return

        s = result["stats"]
        print(f"\n{'=' * 60}")
        print(f"RESULTS: Unit {test_unit}")
        print("=" * 60)
        print(f"Time: {s['elapsed_seconds']:.1f}s")
        print(f"Chunks: {s['chunks_processed']}/{s['chunks_total']}")
        print(f"Dialogues: {s['dialogue_count']}")
        print(f"Grammar sections: {s['grammar_section_count']}")
        print(f"Exercises: {s['exercise_count']}")
        print(f"Vocabulary: {s['vocab_count']}")

        print_sample(result)

        output_path = save_extraction(result, output_dir)
        print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
