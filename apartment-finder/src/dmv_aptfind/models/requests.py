"""Pydantic request models for the Apartment Finder API."""

from pydantic import BaseModel


class ParseUrlRequest(BaseModel):
    """Request body for POST /api/parse-url."""

    url: str


class SearchRequest(BaseModel):
    """Request body for POST /api/search."""

    areaIdentifier: str
    minRoomCount: int | None = None
    maxRoomCount: int | None = None
    minRent: int | None = None
    maxRent: int | None = None
    minSquareMeters: int | None = None
    maxSquareMeters: int | None = None
    currency: str = "SEK"
    markets: list[str] = ["sweden", "norway", "finland"]
    furnished: bool | None = None
    petsAllowed: bool | None = None
    homeType: str | None = None
    firstHand: bool | None = None
    studentHome: bool | None = None
    seniorHome: bool | None = None
    corporateHome: bool | None = None
    sortBy: str = "published_or_bumped_at"
    sortDirection: str = "descending"
