"""
API Dependencies
==================
Shared dependencies for FastAPI endpoints: pagination, filtering, auth.
"""

from fastapi import Query


class PaginationParams:
    """Pagination dependency for list endpoints."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(default=20, ge=1, le=200, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


class SearchParams:
    """Search/filter dependency for list endpoints."""

    def __init__(
        self,
        search: str = Query(default="", description="Global text search"),
        country: str = Query(default="", description="Filter by country name"),
        country_iso2: str = Query(default="", description="Filter by ISO-2 country code"),
    ):
        self.search = search.strip()
        self.country = country.strip()
        self.country_iso2 = country_iso2.strip().upper()
