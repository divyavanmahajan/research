"""Pydantic response models for the Apartment Finder API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str


class SearchResponse(BaseModel):
    """Response for POST /api/search."""

    totalCount: int
    pagesCount: int
    results: list[dict]
