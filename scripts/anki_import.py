#!/usr/bin/env python3
"""
Bulk import Hindi vocabulary to Anki via AnkiConnect.

Creates reversible cards (transliteration <-> meaning) for all extracted vocab.

Usage:
    python scripts/anki_import.py [--dry-run]
"""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ANKI_CONNECT_URL = "http://localhost:8765"
DECK_PREFIX = "Hindi Vocab"
NOTE_TYPE = "Hindi Vocab"
EXTRACTED_DIR = Path(__file__).parent.parent / "study-materials" / "extracted-backup"


def anki_request(action: str, **params) -> dict:
    """Send request to AnkiConnect."""
    request_data = json.dumps({"action": action, "version": 6, "params": params})
    req = urllib.request.Request(
        ANKI_CONNECT_URL,
        data=request_data.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("error"):
                raise Exception(result["error"])
            return result.get("result")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to AnkiConnect: {e}")


def launch_anki_and_wait():
    """Launch Anki and wait for AnkiConnect to be ready."""
    print("Launching Anki...")
    subprocess.Popen(["open", "-a", "Anki"])

    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        try:
            anki_request("version")
            print("AnkiConnect ready.")
            return True
        except ConnectionError:
            pass

    raise ConnectionError("Anki failed to start or AnkiConnect not installed")


def ensure_connection():
    """Ensure AnkiConnect is available, launching Anki if needed."""
    try:
        version = anki_request("version")
        print(f"Connected to AnkiConnect v{version}")
        return True
    except ConnectionError:
        return launch_anki_and_wait()


def create_note_type():
    """Create Hindi Vocab note type if it doesn't exist."""
    existing = anki_request("modelNames")
    if NOTE_TYPE in existing:
        print(f"Note type '{NOTE_TYPE}' already exists")
        return

    print(f"Creating note type '{NOTE_TYPE}'...")
    anki_request(
        "createModel",
        modelName=NOTE_TYPE,
        inOrderFields=["vocab_id", "transliteration", "meaning", "gender", "pos", "unit"],
        css="""
.card {
    font-family: arial;
    font-size: 24px;
    text-align: center;
    color: black;
    background-color: white;
}
.gender { color: #666; font-size: 18px; }
.pos { color: #999; font-size: 14px; }
        """,
        cardTemplates=[
            {
                "Name": "Recognition",
                "Front": "{{transliteration}}",
                "Back": """{{FrontSide}}<hr id="answer">
{{meaning}}
<div class="gender">{{gender}}</div>
<div class="pos">{{pos}}</div>""",
            },
            {
                "Name": "Production",
                "Front": "{{meaning}}",
                "Back": """{{FrontSide}}<hr id="answer">
{{transliteration}}
<div class="gender">{{gender}}</div>""",
            },
        ],
    )
    print("Note type created")


def create_deck(unit_num: int):
    """Create deck for a unit if it doesn't exist."""
    deck_name = f"{DECK_PREFIX}::Unit {unit_num:02d}"
    anki_request("createDeck", deck=deck_name)
    return deck_name


def get_existing_vocab_ids() -> set:
    """Get all existing vocab_ids to avoid duplicates."""
    note_ids = anki_request("findNotes", query=f'"note:{NOTE_TYPE}"')
    if not note_ids:
        return set()

    notes_info = anki_request("notesInfo", notes=note_ids)
    return {note["fields"]["vocab_id"]["value"] for note in notes_info}


def load_vocab(unit_num: int) -> list[dict]:
    """Load vocabulary from extracted JSON."""
    json_path = EXTRACTED_DIR / f"{unit_num:02d}.json"
    if not json_path.exists():
        return []

    with open(json_path) as f:
        data = json.load(f)

    return data.get("vocabulary", [])


def create_vocab_id(unit_num: int, transliteration: str) -> str:
    """Create unique vocab_id."""
    # Normalize: lowercase, remove spaces/punctuation
    clean = "".join(c for c in transliteration.lower() if c.isalnum())
    return f"unit{unit_num:02d}_{clean}"


def prepare_notes(unit_num: int, vocab: list[dict], existing_ids: set) -> list[dict]:
    """Prepare notes for Anki import."""
    deck_name = f"{DECK_PREFIX}::Unit {unit_num:02d}"
    notes = []

    for entry in vocab:
        transliteration = entry.get("transliteration", "").strip()
        meaning = entry.get("meaning", "").strip()

        if not transliteration or not meaning:
            continue

        vocab_id = create_vocab_id(unit_num, transliteration)

        if vocab_id in existing_ids:
            continue

        gender = entry.get("gender", "") or ""
        pos = entry.get("part_of_speech", "") or ""

        notes.append({
            "deckName": deck_name,
            "modelName": NOTE_TYPE,
            "fields": {
                "vocab_id": vocab_id,
                "transliteration": transliteration,
                "meaning": meaning,
                "gender": f"({gender})" if gender else "",
                "pos": pos,
                "unit": str(unit_num),
            },
            "options": {"allowDuplicate": False},
            "tags": [f"hindi::unit{unit_num:02d}"],
        })

    return notes


def dedupe_all_vocab() -> dict[int, list[dict]]:
    """Load all vocab and dedupe by transliteration, keeping first unit occurrence."""
    seen_translits: dict[str, int] = {}  # translit -> first unit
    by_unit: dict[int, list[dict]] = {u: [] for u in range(1, 19)}

    # First pass: find first unit for each transliteration
    for unit_num in range(1, 19):
        vocab = load_vocab(unit_num)
        for entry in vocab:
            translit = entry.get("transliteration", "").strip().lower()
            translit_key = "".join(c for c in translit if c.isalnum())
            if translit_key and translit_key not in seen_translits:
                seen_translits[translit_key] = unit_num
                by_unit[unit_num].append(entry)

    return by_unit


def import_all(dry_run: bool = False):
    """Import all vocabulary to Anki."""
    # Dedupe across all units first
    print("Deduplicating vocabulary (keeping first unit occurrence)...")
    deduped = dedupe_all_vocab()

    print("\nWord count per unit after deduplication:")
    for unit_num in range(1, 19):
        count = len(deduped[unit_num])
        if count > 0:
            print(f"  Unit {unit_num:2d}: {count} words")

    total_unique = sum(len(v) for v in deduped.values())
    print(f"\nTotal unique words: {total_unique}")

    if not dry_run:
        ensure_connection()
        create_note_type()

    existing_ids = set() if dry_run else get_existing_vocab_ids()
    print(f"\nFound {len(existing_ids)} existing cards in Anki")

    total_added = 0
    total_skipped = 0

    for unit_num in range(1, 19):
        vocab = deduped[unit_num]
        if not vocab:
            continue

        if not dry_run:
            create_deck(unit_num)

        notes = prepare_notes(unit_num, vocab, existing_ids)
        skipped = len(vocab) - len(notes)

        if notes and not dry_run:
            results = anki_request("addNotes", notes=notes)
            added = sum(1 for r in results if r is not None)
            failed = len(notes) - added
            if failed > 0:
                print(f"Unit {unit_num}: {added} added, {skipped} skipped, {failed} failed")
            else:
                print(f"Unit {unit_num}: {added} added")
            total_added += added
        else:
            if not dry_run:
                print(f"Unit {unit_num}: {len(notes)} to add, {skipped} already in Anki")
            total_added += len(notes)

        total_skipped += skipped

        # Track new IDs to avoid duplicates within same run
        for note in notes:
            existing_ids.add(note["fields"]["vocab_id"])

    print(f"\nTotal: {total_added} cards {'would be ' if dry_run else ''}added, {total_skipped} skipped")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN - no changes will be made\n")

    try:
        import_all(dry_run=dry_run)
    except ConnectionError as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Anki is installed")
        print("2. AnkiConnect add-on is installed (code: 2055492159)")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
