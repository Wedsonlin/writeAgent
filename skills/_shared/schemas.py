"""Pydantic models mirroring ``schemas/*.schema.json``.

These models give us:

* Run-time validation when a Skill produces structured output.
* A typed surface for the LangGraph state channels.
* Auto-conversion JSON ↔ Python (via ``model_dump``).

The source of truth for cross-team contracts is **still the JSON Schema files**
under ``schemas/``; this module is the Python projection used by Skill 1 / Skill 2.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ----------------------------- writing_task ---------------------------------


class JournalStyleProfile(BaseModel):
    citation_style: Optional[
        Literal["GB/T 7714", "APA", "IEEE", "ACM", "Chicago"]
    ] = None
    tone: Optional[Literal["formal-zh", "formal-en", "narrative"]] = None
    structure_hint: Optional[str] = None


class TargetJournal(BaseModel):
    name: str
    level: Optional[
        Literal[
            "CCF-A", "CCF-B", "CCF-C", "SCI", "EI", "中文核心", "未指定", "其他"
        ]
    ] = "未指定"
    style_profile: Optional[JournalStyleProfile] = None


class WordLimit(BaseModel):
    total: int = Field(ge=1000)
    by_chapter: Optional[dict[str, int]] = None


class ChapterFrameworkItem(BaseModel):
    chapter_id: str
    title: str
    key_points: list[str] = Field(default_factory=list)
    word_budget: Optional[int] = None
    depends_on: Optional[list[str]] = None


class ReferenceSeed(BaseModel):
    id: str
    type: Literal["bibtex", "pdf", "text", "url"]
    path: Optional[str] = None
    raw: Optional[str] = None


class MissingInfoItem(BaseModel):
    field: str
    question: str
    criticality: Literal["blocker", "important", "nice-to-have"]
    suggested_default: Optional[str] = None


class ResearchScope(BaseModel):
    domain: Optional[str] = None
    subtopics: list[str] = Field(default_factory=list)
    boundary: Optional[str] = None


class WritingTask(BaseModel):
    topic: str
    paper_type: Literal[
        "survey", "empirical", "theoretical", "system", "case_study", "position"
    ]
    language: Literal["zh", "en", "bilingual"]
    target_journal: TargetJournal
    word_limit: WordLimit
    core_arguments: list[str] = Field(min_length=1)
    innovation_points: list[str] = Field(default_factory=list)
    research_scope: Optional[ResearchScope] = None
    chapter_framework: list[ChapterFrameworkItem]
    references_seed: list[ReferenceSeed] = Field(default_factory=list)
    missing_info: list[MissingInfoItem] = Field(default_factory=list)


# --------------------------- literature_report ------------------------------


class AlignmentToCore(BaseModel):
    core_argument_index: int = Field(ge=0)
    stance: Literal["supports", "extends", "challenges", "neutral"]
    note: Optional[str] = None


class PaperRecord(BaseModel):
    id: str
    type: Optional[
        Literal["journal", "conference", "preprint", "book", "thesis", "report", "misc"]
    ] = "misc"
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    key_claims: list[str] = Field(default_factory=list)
    evidence_strength: Optional[
        Literal["strong", "moderate", "weak", "anecdotal"]
    ] = None
    alignment_to_core: list[AlignmentToCore] = Field(default_factory=list)
    source_kind: Optional[Literal["bibtex", "pdf", "text", "url"]] = None


class LandscapeCluster(BaseModel):
    name: str
    summary: Optional[str] = None
    paper_ids: list[str]


class ResearchLandscape(BaseModel):
    clusters: list[LandscapeCluster]
    timeline_summary: Optional[str] = None


class FormattedBibliography(BaseModel):
    gb7714: list[str]
    apa: list[str]


class LiteratureReport(BaseModel):
    keywords: list[str] = Field(min_length=1)
    papers: list[PaperRecord]
    research_landscape: ResearchLandscape
    consensus: list[str] = Field(default_factory=list)
    controversies: list[str] = Field(default_factory=list)
    research_gaps: list[str] = Field(default_factory=list)
    citation_style: Literal["GB/T 7714", "APA", "IEEE", "ACM", "Chicago"] = "GB/T 7714"
    formatted_bibliography: FormattedBibliography


# ------------------------- top-level state aliases --------------------------


def empty_state(case_id: str = "unnamed-case", user_request: str = "") -> dict[str, Any]:
    """Return an empty workspace state matching ``state.schema.json``."""
    return {
        "case_id": case_id,
        "user_request": user_request,
        "stage": "init",
        "history": [],
    }
