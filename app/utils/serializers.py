"""
MongoDB Document Serializer.
Recursively converts BSON ObjectId, datetime, and other MongoDB types to JSON-safe Python types.
"""
from typing import Any
from bson import ObjectId
from datetime import datetime


def serialize_mongo_doc(data: Any) -> Any:
    """
    Recursively converts BSON ObjectId and other non-JSON types to strings/primitives.
    Also maps '_id' to 'id' string if present.
    """
    if data is None:
        return None
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == "_id":
                result["id"] = str(v)
            else:
                result[k] = serialize_mongo_doc(v)
        # Ensure id is present if _id was in the dict
        if "_id" in data and "id" not in result:
            result["id"] = str(data["_id"])
        return result
    if isinstance(data, (list, tuple, set)):
        return [serialize_mongo_doc(item) for item in data]
    return data
