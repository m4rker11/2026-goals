"""
Pydantic schemas for Hindi textbook extraction.

Designed for use with instructor (https://github.com/567-labs/instructor)
for structured LLM extraction from textbook markdown.

Storage: study-materials/extracted/units/*.json
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
    """A Hindi example with translation."""
    hindi: str
    transliteration: str | None = None
    english: str


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
# MAIN CONTENT MODELS
# =============================================================================

class VocabularyEntry(BaseModel):
    """A vocabulary word - maps to an Anki card."""
    id: str                              # UUID for stability
    slug: str                            # 'u03-kitab' for display
    anki_note_id: int | None = None      # Anki's note ID once synced

    # Core fields
    hindi: str                           # किताब
    transliteration: str                 # kitāb
    meaning: str                         # book
    part_of_speech: PartOfSpeech

    # Noun-specific
    gender: Gender | None = None
    oblique_singular: str | None = None  # कमरे for कमरा
    oblique_plural: str | None = None    # कमरों

    # Verb-specific
    verb_forms: VerbForms | None = None

    # Metadata
    priority: Priority = Priority.COMMON
    examples: list[Example] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    audio: str | None = None             # Future: audio file ref
    source_ref: str                      # '3a', '3.1' etc.


class GrammarConcept(BaseModel):
    """A grammar rule or construction."""
    id: str                              # UUID
    slug: str                            # 'oblique-case'
    name: str                            # 'The Oblique Case'
    explanation: str                     # 2-3 sentence summary
    examples: list[Example] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)  # Concept slugs
    difficulty: Difficulty = Difficulty.BEGINNER
    source_ref: str                      # '3.2'


class Exercise(BaseModel):
    """A practice exercise from the textbook."""
    id: str                              # UUID
    slug: str                            # 'ex-3a1'
    instruction: str                     # 'Translate these sentences'
    exercise_type: ExerciseType
    items: list[ExerciseItem]
    concepts_practiced: list[str] = Field(default_factory=list)  # Concept slugs
    source_ref: str                      # '3a'


class Section(BaseModel):
    """A section within a unit (dialogue or grammar)."""
    id: str                              # UUID
    slug: str                            # '3a' or '3.1'
    label: str                           # 'Pratap's mother phones from London'
    section_type: SectionType
    order: int                           # For sorting within unit


class Unit(BaseModel):
    """A complete textbook unit with all content."""
    unit_number: int
    title: str
    sections: list[Section] = Field(default_factory=list)
    vocabulary: list[VocabularyEntry] = Field(default_factory=list)
    concepts: list[GrammarConcept] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)


# =============================================================================
# INDEX MODEL (for study-materials/extracted/index.json)
# =============================================================================

class UnitSummary(BaseModel):
    """Summary info for index.json."""
    unit_number: int
    title: str
    vocab_count: int
    concept_count: int
    exercise_count: int


class ExtractedIndex(BaseModel):
    """Index of all extracted units."""
    units: list[UnitSummary]
    total_vocab: int
    total_concepts: int
