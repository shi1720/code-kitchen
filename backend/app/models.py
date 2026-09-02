"""Domain models.

The vocabulary here deliberately mirrors the evaluation dataset schemas:

- postings CSV : ``id, from, to, type, description``
- drafts CSV   : ``id, jobId, type, contents, status``

so an imported row maps 1:1 onto a domain object with no lossy renaming.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums — the four pipeline phases named by the problem statement.
# ---------------------------------------------------------------------------


class Status(StrEnum):
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECT = "reject"


class DraftType(StrEnum):
    COVER_LETTER = "cover_letter"
    FOLLOW_UP_EMAIL = "follow_up_email"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"


class NudgeStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DISMISSED = "dismissed"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class StatusChange(BaseModel):
    from_status: Status | None = None
    to_status: Status
    at: datetime
    note: str = ""


class Application(BaseModel):
    id: str = Field(default_factory=new_id)
    uid: str
    external_id: str | None = None  # id column of an imported posting
    company: str = ""
    role: str
    location: str = ""
    job_type: str = ""  # full-time | contract | internship | ...
    description: str = ""  # raw posting text — the grounding source
    skills: list[str] = Field(default_factory=list)
    posting_from: datetime | None = None
    posting_to: datetime | None = None
    applied_at: datetime = Field(default_factory=utcnow)
    status: Status = Status.APPLIED
    status_history: list[StatusChange] = Field(default_factory=list)
    last_activity_at: datetime = Field(default_factory=utcnow)
    source: str = "manual"  # manual | import
    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self, at: datetime | None = None) -> None:
        now = at or utcnow()
        self.last_activity_at = now
        self.updated_at = now


class Draft(BaseModel):
    id: str = Field(default_factory=new_id)
    uid: str
    application_id: str
    external_id: str | None = None  # id column of an imported draft
    type: DraftType
    subject: str = ""
    contents: str
    status: DraftStatus = DraftStatus.DRAFT
    source: str = "generated"  # generated | imported | edited
    model: str = ""  # which Gemini model produced it, if generated
    grounded_on: list[str] = Field(default_factory=list)  # draft ids used as voice references
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Nudge(BaseModel):
    id: str = Field(default_factory=new_id)
    uid: str
    application_id: str
    rule: str
    touch: int = 1  # 1st, 2nd, 3rd follow-up in the cadence
    headline: str
    detail: str = ""
    due_at: datetime
    status: NudgeStatus = NudgeStatus.PENDING
    draft_id: str | None = None  # auto-drafted follow-up attached to the nudge
    dedupe_key: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Profile(BaseModel):
    uid: str
    name: str = ""
    headline: str = ""
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    tone: str = "warm, direct, confident"
    achievements: str = ""


# ---------------------------------------------------------------------------
# Import pipeline reporting
# ---------------------------------------------------------------------------


class RowError(BaseModel):
    row: int
    reason: str


class FileReport(BaseModel):
    filename: str = ""
    total_rows: int = 0
    accepted: int = 0
    updated: int = 0  # idempotent re-imports resolve to updates, not dupes
    rejected: list[RowError] = Field(default_factory=list)


class ImportReport(BaseModel):
    id: str = Field(default_factory=new_id)
    uid: str = ""
    postings: FileReport = Field(default_factory=FileReport)
    drafts: FileReport = Field(default_factory=FileReport)
    linked_drafts: int = 0
    orphaned_drafts: int = 0  # drafts whose jobId matched no posting
    embedded: int = 0
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# API request/response shapes
# ---------------------------------------------------------------------------


class ApplicationCreate(BaseModel):
    company: str = ""
    role: str
    location: str = ""
    job_type: str = ""
    description: str = ""
    applied_at: datetime | None = None
    status: Status = Status.APPLIED
    notes: str = ""


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    job_type: str | None = None
    description: str | None = None
    status: Status | None = None
    status_note: str = ""
    notes: str | None = None


class GenerateRequest(BaseModel):
    type: DraftType
    instructions: str = ""  # optional user steering, e.g. "mention the referral"


class DraftUpdate(BaseModel):
    subject: str | None = None
    contents: str | None = None
    status: DraftStatus | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    headline: str | None = None
    years_experience: float | None = None
    skills: list[str] | None = None
    tone: str | None = None
    achievements: str | None = None


class ScanReport(BaseModel):
    scanned: int = 0
    nudges_created: int = 0
    drafts_generated: int = 0
    duration_ms: int = 0
