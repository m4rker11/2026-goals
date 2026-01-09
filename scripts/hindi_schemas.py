"""
Pydantic schemas for Hindi textbook extraction.

Designed for use with instructor (https://github.com/567-labs/instructor)
for structured LLM extraction from textbook markdown.

Storage: study-materials/extracted/
  - raw/*.json        Per-unit raw extractions
  - vocabulary.json   Global canonical vocabulary
  - grammar.json      Global grammar concepts
  - units/*.json      Per-unit views with references
  - index.json        Summary stats
"""

from enum import Enum
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class PartOfSpeech(str, Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adj"
    ADVERB = "adv"
    POSTPOSITION = "postposition"
    PRONOUN = "pronoun"
    CONJUNCTION = "conjunction"
    PARTICLE = "particle"
    INTERJECTION = "interjection"
    COMPOUND_VERB = "compound_verb"  # e.g., काम करना


class Gender(str, Enum):
    MASCULINE = "m"
    FEMININE = "f"


class SectionType(str, Enum):
    DIALOGUE = "dialogue"
    GRAMMAR = "grammar"


class ExerciseType(str, Enum):
    TRANSLATION = "translation"
    FILL_BLANK = "fill_blank"
    MCQ = "mcq"
    COMPREHENSION = "comprehension"
    MATCHING = "matching"
    WRITING = "writing"


class Difficulty(int, Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class Priority(int, Enum):
    CORE = 1        # Must learn
    COMMON = 2      # Should learn
    SUPPLEMENTARY = 3  # Nice to have


# =============================================================================
# COMPONENT MODELS
# =============================================================================

class Example(BaseModel):
    """A Hindi example with translation and source tracking."""
    hindi: str
    transliteration: str | None = None
    english: str
    source_unit: int | None = None      # Which unit this example came from
    source_section: str | None = None   # '3a', '3.1', etc.


class VerbForms(BaseModel):
    """Verb conjugation forms for Hindi verbs."""
    infinitive: str              # करना
    stem: str                    # कर
    habitual_m: str | None = None   # करता
    habitual_f: str | None = None   # करती
    perfective_m: str | None = None  # किया
    perfective_f: str | None = None  # की


class ExerciseItem(BaseModel):
    """A single exercise question/task."""
    prompt: str
    answer: str | None = None
    choices: list[str] | None = None  # For MCQ
    hints: list[str] = Field(default_factory=list)


# =============================================================================
# RAW EXTRACTION MODELS (Phase 1 - per chunk/unit)
# =============================================================================

class RawVocabEntry(BaseModel):
    """Vocabulary entry as extracted from a single chunk.

    The LLM provides both canonical and encountered forms.
    """
    # Canonical/dictionary form (for deduplication)
    hindi: str                           # Canonical: लड़का not लड़के
    transliteration: str                 # Canonical: laṛkā
    meaning: str
    part_of_speech: str                  # Use string for flexibility in extraction

    # Form as encountered in text (if different from canonical)
    encountered_form: str | None = None  # लड़के (oblique/plural)
    encountered_translit: str | None = None

    # Noun-specific
    gender: str | None = None            # "m" or "f"

    # Context from extraction
    examples: list[Example] = Field(default_factory=list)


class RawGrammarPoint(BaseModel):
    """Grammar point as extracted from a single chunk."""
    name: str
    explanation: str
    examples: list[Example] = Field(default_factory=list)


class RawChunkExtract(BaseModel):
    """Extraction result from a single chunk of text."""
    vocabulary: list[RawVocabEntry] = Field(default_factory=list)
    grammar_points: list[RawGrammarPoint] = Field(default_factory=list)


class RawUnitExtract(BaseModel):
    """Raw extraction for a complete unit (merged chunks, before global dedup)."""
    unit_number: int
    title: str | None = None
    vocabulary: list[RawVocabEntry] = Field(default_factory=list)
    grammar_points: list[RawGrammarPoint] = Field(default_factory=list)
    extraction_stats: dict = Field(default_factory=dict)  # chunks, time, etc.


# =============================================================================
# MERGED/CANONICAL MODELS (Phase 2 - global)
# =============================================================================

class VocabularyEntry(BaseModel):
    """A canonical vocabulary entry - maps to one Anki card.

    Deduplication key: (hindi, part_of_speech)
    Lives in earliest unit where first encountered.
    Examples aggregated from all units.
    """
    id: str                              # UUID for stability

    # Canonical/dictionary form
    hindi: str                           # लड़का (singular direct)
    transliteration: str                 # laṛkā
    meaning: str
    part_of_speech: PartOfSpeech

    # Noun-specific
    gender: Gender | None = None
    inflections: dict[str, str] | None = None  # {"obl_sg": "लड़के", "obl_pl": "लड़कों", ...}

    # Verb-specific
    verb_forms: VerbForms | None = None

    # Provenance tracking
    first_seen_unit: int                 # Unit where first introduced
    first_seen_section: str | None = None
    units_encountered: list[int] = Field(default_factory=list)  # All units [3, 5, 7]

    # Aggregated examples from ALL encounters (with source tracking)
    examples: list[Example] = Field(default_factory=list)

    # Metadata
    priority: Priority = Priority.COMMON
    tags: list[str] = Field(default_factory=list)
    anki_note_id: int | None = None      # Anki's note ID once synced


class GrammarConcept(BaseModel):
    """A grammar rule or construction."""
    id: str                              # UUID
    slug: str                            # 'oblique-case'
    name: str                            # 'The Oblique Case'
    explanation: str                     # 2-3 sentence summary
    examples: list[Example] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)  # Concept slugs
    difficulty: Difficulty = Difficulty.BEGINNER
    first_seen_unit: int
    first_seen_section: str | None = None
    units_encountered: list[int] = Field(default_factory=list)


class Exercise(BaseModel):
    """A practice exercise from the textbook."""
    id: str                              # UUID
    slug: str                            # 'ex-3a1'
    instruction: str                     # 'Translate these sentences'
    exercise_type: ExerciseType
    items: list[ExerciseItem]
    concepts_practiced: list[str] = Field(default_factory=list)  # Concept slugs
    source_unit: int
    source_section: str


class Section(BaseModel):
    """A section within a unit (dialogue or grammar)."""
    id: str                              # UUID
    slug: str                            # '3a' or '3.1'
    label: str                           # 'Pratap's mother phones from London'
    section_type: SectionType
    order: int                           # For sorting within unit


# =============================================================================
# UNIT AND INDEX MODELS
# =============================================================================

class UnitView(BaseModel):
    """Per-unit view with references to canonical vocabulary."""
    unit_number: int
    title: str
    sections: list[Section] = Field(default_factory=list)

    # IDs of vocab/concepts first introduced in this unit
    new_vocabulary_ids: list[str] = Field(default_factory=list)
    new_concept_ids: list[str] = Field(default_factory=list)

    # IDs of vocab/concepts reviewed (appeared before)
    review_vocabulary_ids: list[str] = Field(default_factory=list)
    review_concept_ids: list[str] = Field(default_factory=list)

    # Exercises for this unit
    exercises: list[Exercise] = Field(default_factory=list)


class UnitSummary(BaseModel):
    """Summary info for index.json."""
    unit_number: int
    title: str
    new_vocab_count: int
    review_vocab_count: int
    new_concept_count: int
    review_concept_count: int
    exercise_count: int


class MergedCorpus(BaseModel):
    """The complete merged extraction result."""
    vocabulary: list[VocabularyEntry] = Field(default_factory=list)
    concepts: list[GrammarConcept] = Field(default_factory=list)
    units: list[UnitView] = Field(default_factory=list)

    # Stats
    total_vocab: int = 0
    total_concepts: int = 0
    total_examples: int = 0


class ExtractedIndex(BaseModel):
    """Index of all extracted units."""
    units: list[UnitSummary]
    total_vocab: int
    total_concepts: int
    total_examples: int
    extraction_model: str | None = None
    extraction_date: str | None = None
