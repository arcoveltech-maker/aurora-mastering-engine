"""Common response schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from datetime import datetime

from pydantic import BaseModel


class AuroraError(BaseModel):
    error_code: str
    message: str
    severity: str
    details: dict[str, Any] | None = None


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime

