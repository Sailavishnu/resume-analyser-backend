"""
Shared base types, ObjectId handling, and common response wrappers.
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, field_validator
from bson import ObjectId

T = TypeVar("T")


def str_oid(oid) -> str:
    """Convert a pymongo ObjectId (or string) to plain string."""
    return str(oid)


class PyObjectId(str):
    """Pydantic-compatible ObjectId field that serialises as a string."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError(f"Invalid ObjectId: {v!r}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(cls.validate)


# ─── Response wrappers ────────────────────────────────────────────────────────

class DataResponse(BaseModel, Generic[T]):
    data: T


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta


class MessageResponse(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
