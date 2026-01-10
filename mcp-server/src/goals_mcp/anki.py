"""
AnkiConnect client for querying vocabulary mastery.

Connects to Anki desktop via AnkiConnect API to get card intervals
and compute mastery tiers for practice prompt generation.
"""

import asyncio
import json
import logging
import subprocess
import urllib.request
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

ANKI_CONNECT_URL = "http://localhost:8765"
NOTE_TYPE = "Hindi Vocab"


class MasteryTier(Enum):
    NEW = "new"
    LEARNING = "learning"
    YOUNG = "young"
    MATURE = "mature"


@dataclass
class VocabMastery:
    vocab_id: str
    transliteration: str
    meaning: str
    unit: int
    tier: MasteryTier
    interval_days: int


# Global cache
_mastery_cache: dict[str, VocabMastery] = {}
_cache_loaded: bool = False


def _anki_request(action: str, **params) -> dict:
    """Send synchronous request to AnkiConnect."""
    request_data = json.dumps({"action": action, "version": 6, "params": params})
    req = urllib.request.Request(
        ANKI_CONNECT_URL,
        data=request_data.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("error"):
                raise Exception(result["error"])
            return result.get("result")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to AnkiConnect: {e}")


def _launch_anki() -> bool:
    """Launch Anki application (macOS)."""
    try:
        subprocess.Popen(["open", "-a", "Anki"])
        return True
    except Exception as e:
        logger.error(f"Failed to launch Anki: {e}")
        return False


def _interval_to_tier(interval_days: int) -> MasteryTier:
    """Convert interval in days to mastery tier."""
    if interval_days == 0:
        return MasteryTier.NEW
    elif interval_days <= 7:
        return MasteryTier.LEARNING
    elif interval_days <= 21:
        return MasteryTier.YOUNG
    else:
        return MasteryTier.MATURE


def _load_mastery_sync() -> dict[str, VocabMastery]:
    """Load mastery data from Anki (synchronous)."""
    mastery = {}

    # Find all Hindi vocab notes
    note_ids = _anki_request("findNotes", query=f'"note:{NOTE_TYPE}"')
    if not note_ids:
        logger.info("No Hindi vocab notes found in Anki")
        return mastery

    # Get note details
    notes_info = _anki_request("notesInfo", notes=note_ids)

    # Get ALL cards for this note type in ONE call (not per-note!)
    all_card_ids = _anki_request("findCards", query=f'"note:{NOTE_TYPE}"')

    # Get card info in one batch
    cards_info = _anki_request("cardsInfo", cards=all_card_ids) if all_card_ids else []

    # Group cards by note ID
    note_to_cards = {}
    card_intervals = {}
    for card in cards_info:
        note_id = card["note"]
        card_id = card["cardId"]
        if note_id not in note_to_cards:
            note_to_cards[note_id] = []
        note_to_cards[note_id].append(card_id)
        card_intervals[card_id] = card.get("interval", 0)

    # Build mastery data
    for note in notes_info:
        fields = note["fields"]
        vocab_id = fields.get("vocab_id", {}).get("value", "")
        if not vocab_id:
            continue

        # Get minimum interval across all cards for this note
        note_card_ids = note_to_cards.get(note["noteId"], [])
        intervals = [card_intervals.get(cid, 0) for cid in note_card_ids]
        min_interval = min(intervals) if intervals else 0

        try:
            unit = int(fields.get("unit", {}).get("value", "0"))
        except ValueError:
            unit = 0

        mastery[vocab_id] = VocabMastery(
            vocab_id=vocab_id,
            transliteration=fields.get("transliteration", {}).get("value", ""),
            meaning=fields.get("meaning", {}).get("value", ""),
            unit=unit,
            tier=_interval_to_tier(min_interval),
            interval_days=min_interval,
        )

    return mastery


async def load_mastery_async() -> bool:
    """Load mastery data asynchronously. Called on MCP connect."""
    global _mastery_cache, _cache_loaded

    def _load():
        global _mastery_cache, _cache_loaded
        try:
            # Try to connect
            try:
                _anki_request("version")
            except ConnectionError:
                # Try launching Anki
                logger.info("Anki not running, attempting to launch...")
                _launch_anki()
                # Wait for Anki to start
                import time
                for _ in range(15):
                    time.sleep(1)
                    try:
                        _anki_request("version")
                        break
                    except ConnectionError:
                        pass
                else:
                    raise ConnectionError("Failed to connect to Anki after launch")

            _mastery_cache = _load_mastery_sync()
            _cache_loaded = True
            logger.info(f"Loaded mastery for {len(_mastery_cache)} vocab items")
            return True

        except Exception as e:
            logger.warning(f"Failed to load Anki mastery: {e}")
            _cache_loaded = True  # Mark as loaded even on failure (graceful degradation)
            return False

    # Run in thread pool to not block
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _load)


def get_mastery_cache() -> dict[str, VocabMastery]:
    """Get cached mastery data."""
    return _mastery_cache


def is_cache_loaded() -> bool:
    """Check if cache has been loaded."""
    return _cache_loaded


def get_vocab_by_tier(tier: MasteryTier, unit: int | None = None) -> list[VocabMastery]:
    """Get vocabulary items by mastery tier, optionally filtered by unit."""
    result = []
    for vocab in _mastery_cache.values():
        if vocab.tier == tier:
            if unit is None or vocab.unit <= unit:
                result.append(vocab)
    return result


def get_vocab_for_practice(
    current_unit: int,
    count: int = 20,
    weights: dict[MasteryTier, float] | None = None,
) -> list[VocabMastery]:
    """
    Get vocabulary for practice, weighted by mastery tier.

    Args:
        current_unit: Current unit being studied (includes vocab from this and prior units)
        count: Number of vocab items to return
        weights: Weight for each tier (default: new=0.1, learning=0.4, young=0.35, mature=0.15)

    Returns:
        List of VocabMastery items selected by weighted random sampling
    """
    import random

    if weights is None:
        weights = {
            MasteryTier.NEW: 0.10,
            MasteryTier.LEARNING: 0.40,
            MasteryTier.YOUNG: 0.35,
            MasteryTier.MATURE: 0.15,
        }

    # Get vocab by tier (only from current and prior units)
    by_tier = {tier: [] for tier in MasteryTier}
    for vocab in _mastery_cache.values():
        if vocab.unit <= current_unit:
            by_tier[vocab.tier].append(vocab)

    # Calculate how many to pick from each tier
    tier_counts = {}
    remaining = count
    for tier, weight in weights.items():
        tier_count = min(int(count * weight), len(by_tier[tier]))
        tier_counts[tier] = tier_count
        remaining -= tier_count

    # Distribute remaining across non-empty tiers
    for tier in MasteryTier:
        if remaining <= 0:
            break
        available = len(by_tier[tier]) - tier_counts[tier]
        if available > 0:
            add = min(remaining, available)
            tier_counts[tier] += add
            remaining -= add

    # Random sample from each tier
    result = []
    for tier, tier_count in tier_counts.items():
        if tier_count > 0 and by_tier[tier]:
            sampled = random.sample(by_tier[tier], min(tier_count, len(by_tier[tier])))
            result.extend(sampled)

    # Shuffle final result
    random.shuffle(result)
    return result[:count]
