"""
Standard pagination helpers for MongoDB queries and response formatting.
"""
from typing import Any, TypeVar, Generic
from pydantic import BaseModel
from pymongo.database import Database
from pymongo.collection import Collection

from app.schemas.common import PaginationMeta, PaginatedResponse

T = TypeVar("T", bound=BaseModel)


def paginate_query(
    collection: Collection,
    filter_dict: dict,
    page: int = 1,
    page_size: int = 20,
    sort_field: str = "_id",
    sort_direction: int = -1,
) -> tuple[list[dict], PaginationMeta]:
    """
    Execute a paginated MongoDB query and return results + pagination metadata.
    
    Args:
        collection: PyMongo collection
        filter_dict: MongoDB query filter
        page: 1-based page number
        page_size: Items per page (clamped to max 100)
        sort_field: Field to sort by
        sort_direction: 1 (ascending) or -1 (descending)
    
    Returns:
        (documents, pagination_meta)
    """
    # Clamp page size
    page_size = max(1, min(page_size, 100))
    page = max(1, page)
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get total count
    total = collection.count_documents(filter_dict)
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    # Execute paginated query
    cursor = collection.find(filter_dict).sort(sort_field, sort_direction).skip(skip).limit(page_size)
    documents = list(cursor)
    
    # Create pagination metadata
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    
    return documents, pagination


def create_paginated_response(
    items: list[T],
    pagination: PaginationMeta,
) -> PaginatedResponse[T]:
    """
    Create a standardised paginated response.
    """
    return PaginatedResponse(data=items, pagination=pagination)


def parse_pagination_params(page: int | None = None, page_size: int | None = None) -> tuple[int, int]:
    """
    Parse and validate pagination parameters with sensible defaults.
    """
    page = max(1, page or 1)
    page_size = max(1, min(page_size or 20, 100))
    return page, page_size