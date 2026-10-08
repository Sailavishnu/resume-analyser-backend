"""
Simple auth for testing - no real authentication
"""
from fastapi import HTTPException

def get_current_user():
    """Mock user for testing"""
    return {"user_id": "test_user_123", "username": "testuser", "email": "test@example.com"}