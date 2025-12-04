"""
Pagination Utility Module

Provides standardized pagination helpers for all API endpoints.
"""
from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = 1
    page_size: int = 10

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    class Config:
        from_attributes = True


async def paginate(
    db: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 10,
    count_query: Optional[Select] = None
) -> dict:
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        db: Database session
        query: Base SQLAlchemy query
        page: Page number (1-indexed)
        page_size: Items per page
        count_query: Optional custom count query

    Returns:
        Dictionary with items, total, page, page_size, total_pages, has_next, has_previous
    """
    # Ensure valid page and page_size
    page = max(1, page)
    page_size = max(1, min(100, page_size))  # Cap at 100 items per page

    offset = (page - 1) * page_size

    # Get total count
    if count_query is not None:
        count_result = await db.execute(count_query)
    else:
        # Create count query from base query
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_stmt)

    total = count_result.scalar() or 0
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # Apply pagination
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int
) -> dict:
    """
    Create a paginated response dictionary.

    Args:
        items: List of items for current page
        total: Total count of all items
        page: Current page number
        page_size: Items per page

    Returns:
        Paginated response dictionary
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }
