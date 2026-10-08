#!/usr/bin/env python3
"""
Minimal test for coding platform without heavy ML dependencies
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_problems():
    """Test if problems are inserted correctly"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ppp_db
    collection = db.coding_problems
    
    # Count problems
    count = await collection.count_documents({})
    print(f"Total problems in database: {count}")
    
    # Get first few problems
    cursor = collection.find({}).limit(5)
    problems = await cursor.to_list(length=5)
    
    print("\nFirst 5 problems:")
    for i, problem in enumerate(problems, 1):
        print(f"{i}. {problem.get('title', 'No title')} ({problem.get('difficulty', 'Unknown')} - {problem.get('category', 'Unknown')})")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_problems())