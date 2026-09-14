"""
MongoDB client lifecycle management.

A single AsyncIOMotorClient (via motor) would be ideal, but since the spec
mandates pymongo and Motor isn't in requirements, we use pymongo's standard
client wrapped in FastAPI's async startup/shutdown events.

All DB access is via async route handlers that call synchronous pymongo
operations in a thread pool using FastAPI's run_in_threadpool / asyncio.
Because pymongo 4.x is thread-safe we get one shared client.
"""

from pymongo import MongoClient
from pymongo.database import Database
from app.core.config import settings

_client: MongoClient | None = None
_db: Database | None = None


def connect_db() -> None:
    """Call once at application startup."""
    global _client, _db
    _client = MongoClient(settings.MONGO_URI)
    _db = _client[settings.MONGO_DB_NAME]
    # Ping to validate connection early
    _client.admin.command("ping")


def close_db() -> None:
    """Call once at application shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> Database:
    """Return the database instance (sync, for services and scripts)."""
    if _db is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _db


# ─── FastAPI dependency ───────────────────────────────────────────────────────

async def get_database() -> Database:
    """
    FastAPI dependency — yields the shared pymongo Database.
    Routes use `db: Database = Depends(get_database)`.
    """
    return get_db()
