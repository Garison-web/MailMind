from typing import Literal

from pydantic import BaseModel, Field


class EmailInput(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10000)


class AnalysisPayload(BaseModel):
    """The structured fields the LLM must return for every email."""

    intent: str
    category: str
    priority: Literal["Critical", "High", "Medium", "Low"]
    urgency: Literal["Urgent", "Normal"]
    response_required: bool
    deadline: str | None = None
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    dates_times: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    summary: str
    priority_reason: str
    reply_draft: str
    confidence: int = Field(ge=0, le=100)


class AnalysisResult(AnalysisPayload):
    """Validated analysis plus the processor that produced it."""

    source: str
