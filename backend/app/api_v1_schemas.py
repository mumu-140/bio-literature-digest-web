from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LiteratureBatchRequest(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=200)


class ReportTaskCreate(BaseModel):
    report_type: Literal["weekly", "monthly"]
    parameters: dict[str, Any] = Field(default_factory=dict)


class ReportArtifactCreate(BaseModel):
    format: Literal["markdown", "json"]
    content: str = Field(min_length=1, max_length=2_000_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleSuggestionCreate(BaseModel):
    baseline_sha256: str = Field(min_length=64, max_length=64)
    proposed_content: str = Field(min_length=1, max_length=1_000_000)
    summary: str = Field(default="", max_length=4000)
