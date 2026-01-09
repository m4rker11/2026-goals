"""
Pydantic schemas for Hindi textbook extraction.

Captures full learning content:
- Dialogues with speaker turns
- Grammar rules and patterns
- Exercises (comprehension, translation, writing)
- Vocabulary tied to sections

Storage: study-materials/extracted/
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
    COMPOUND_VERB = "compound_verb"
    PHRASE = "phrase"


class Gender(str, Enum):
    MASCULINE = "m"
    FEMININE = "f"


class SectionType(str, Enum):
    DIALOGUE = "dialogue"
    GRAMMAR = "grammar"
    EXERCISE = "exercise"
    VOCAB_LIST = "vocab_list"


class ExerciseType(str, Enum):
    COMPREHENSION = "comprehension"  # Questions about dialogue
    TRANSLATION = "translation"       # Translate sentences
    FILL_BLANK = "fill_blank"
    WRITING = "writing"              # Write dialogue/description
    MATCHING = "matching"
    MCQ = "mcq"


class Difficulty(int, Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class Priority(int, Enum):
    CORE = 1
    COMMON = 2
    SUPPLEMENTARY = 3


# =============================================================================
# TRILINGUAL TEXT (Hindi + Transliteration + English)
# =============================================================================

class TriText(BaseModel):
    """Text in all three forms."""
    hindi: str
    transliteration: str
    english: str


# =============================================================================
# DIALOGUE COMPONENTS
# =============================================================================

class DialogueTurn(BaseModel):
    """A single speaker turn in a dialogue."""
    speaker: str                    # "Anita", "Pratap", etc.
    hindi: str
    transliteration: str
    english: str


class Dialogue(BaseModel):
    """A complete dialogue section (e.g., 3a, 3b)."""
    section_id: str                 # "3a", "3b"
    title: str                      # "Pratap's mother phones from London"
    turns: list[DialogueTurn]
    context: str | None = None      # Setting/situation description


# =============================================================================
# GRAMMAR COMPONENTS
# =============================================================================

class GrammarExample(BaseModel):
    """An example demonstrating a grammar point."""
    hindi: str
    transliteration: str
    english: str
    notes: str | None = None        # Additional explanation


class GrammarRule(BaseModel):
    """A specific grammar rule or pattern."""
    rule: str                       # The rule statement
    pattern: str | None = None      # Pattern like "X + में = in X"
    examples: list[GrammarExample] = Field(default_factory=list)


class GrammarTable(BaseModel):
    """A declension/conjugation table."""
    title: str                      # "Noun cases", "Pronoun oblique forms"
    headers: list[str]              # Column headers
    rows: list[dict[str, str]]      # Each row as dict


class GrammarSection(BaseModel):
    """A grammar explanation section (e.g., 3.1, 3.2)."""
    section_id: str                 # "3.1", "3.2"
    title: str                      # "Simple postpositions"
    explanation: str                # Main explanation text
    rules: list[GrammarRule] = Field(default_factory=list)
    tables: list[GrammarTable] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)  # Bullet points to remember


# =============================================================================
# EXERCISE COMPONENTS
# =============================================================================

class ExerciseItem(BaseModel):
    """A single exercise question."""
    number: int | str
    prompt: TriText | str           # Question/instruction
    answer: TriText | str | None = None
    choices: list[str] | None = None  # For MCQ


class Exercise(BaseModel):
    """An exercise section."""
    exercise_id: str                # "3a.1", "3b.2"
    title: str | None = None
    instruction: str                # "Translate these sentences"
    exercise_type: ExerciseType
    items: list[ExerciseItem] = Field(default_factory=list)
    based_on: str | None = None     # "Dialogue 3a" if comprehension


# =============================================================================
# VOCABULARY
# =============================================================================

class VocabEntry(BaseModel):
    """A vocabulary word."""
    hindi: str                      # Canonical form
    transliteration: str
    meaning: str
    part_of_speech: str
    gender: str | None = None       # "m" or "f"
    encountered_form: str | None = None  # If text had inflected form
    examples: list[TriText] = Field(default_factory=list)


# =============================================================================
# RAW EXTRACTION (from LLM)
# =============================================================================

class RawUnitExtract(BaseModel):
    """Complete extraction from a unit."""
    unit_number: int
    unit_title: str

    # Content sections
    dialogues: list[Dialogue] = Field(default_factory=list)
    grammar_sections: list[GrammarSection] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)

    # Vocabulary (extracted from all sections)
    vocabulary: list[VocabEntry] = Field(default_factory=list)


# =============================================================================
# MERGED/CANONICAL (after cross-unit deduplication)
# =============================================================================

class Example(BaseModel):
    """Example with source tracking."""
    hindi: str
    transliteration: str | None = None
    english: str
    source_unit: int | None = None
    source_section: str | None = None


class VocabularyEntry(BaseModel):
    """Canonical vocabulary entry for Anki."""
    id: str
    hindi: str
    transliteration: str
    meaning: str
    part_of_speech: PartOfSpeech
    gender: Gender | None = None
    inflections: dict[str, str] | None = None

    # Provenance
    first_seen_unit: int
    first_seen_section: str | None = None
    units_encountered: list[int] = Field(default_factory=list)

    # Aggregated examples
    examples: list[Example] = Field(default_factory=list)

    # Metadata
    priority: Priority = Priority.COMMON
    tags: list[str] = Field(default_factory=list)
    anki_note_id: int | None = None


class GrammarConcept(BaseModel):
    """Canonical grammar concept."""
    id: str
    slug: str
    name: str
    explanation: str
    rules: list[GrammarRule] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.BEGINNER
    first_seen_unit: int
    first_seen_section: str | None = None
    units_encountered: list[int] = Field(default_factory=list)


# =============================================================================
# UNIT VIEW (per-unit with references)
# =============================================================================

class UnitView(BaseModel):
    """Complete unit with all content."""
    unit_number: int
    title: str

    # Full content preserved
    dialogues: list[Dialogue] = Field(default_factory=list)
    grammar_sections: list[GrammarSection] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)

    # References to canonical vocab (for dedup tracking)
    new_vocabulary_ids: list[str] = Field(default_factory=list)
    review_vocabulary_ids: list[str] = Field(default_factory=list)


# =============================================================================
# INDEX
# =============================================================================

class UnitSummary(BaseModel):
    """Summary for index."""
    unit_number: int
    title: str
    dialogue_count: int
    grammar_section_count: int
    exercise_count: int
    new_vocab_count: int
    review_vocab_count: int


class ExtractedIndex(BaseModel):
    """Master index."""
    units: list[UnitSummary]
    total_vocab: int
    total_grammar_concepts: int
    total_exercises: int
    extraction_model: str | None = None
    extraction_date: str | None = None


class MergedCorpus(BaseModel):
    """Complete extracted corpus."""
    vocabulary: list[VocabularyEntry] = Field(default_factory=list)
    grammar_concepts: list[GrammarConcept] = Field(default_factory=list)
    units: list[UnitView] = Field(default_factory=list)
    total_vocab: int = 0
    total_concepts: int = 0
    total_examples: int = 0
