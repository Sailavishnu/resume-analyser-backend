"""
MongoDB Index Creation Script

Creates all required indexes for the Resume AI & Placement Platform.
Run this before deploying to production or when setting up a new environment.
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.db.mongodb import connect_db, get_db
from app.db.indexes import create_all_indexes


def main():
    """Create all MongoDB indexes."""
    print("🔍 MongoDB Index Creation Script")
    print("=" * 50)
    
    # Connect to database
    print(f"📡 Connecting to MongoDB: {settings.MONGO_DB_NAME}")
    try:
        connect_db()
        db = get_db()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Create indexes
    print("\n📝 Creating indexes...")
    try:
        create_all_indexes()
        print("✅ All indexes created successfully")
    except Exception as e:
        print(f"❌ Failed to create indexes: {e}")
        sys.exit(1)
    
    # Verify indexes were created
    print("\n🔎 Verifying created indexes...")
    collections_with_indexes = [
        "users", "user_profiles", "resumes", "resume_analyses", 
        "jobs", "applications", "interviews", "assessments",
        "notifications", "analytics_events", "roadmaps", "recommendations"
    ]
    
    total_indexes = 0
    for collection_name in collections_with_indexes:
        try:
            collection = db[collection_name]
            indexes = list(collection.list_indexes())
            index_count = len(indexes)
            total_indexes += index_count
            print(f"  📄 {collection_name}: {index_count} indexes")
            
            # Show index details for important collections
            if collection_name in ["users", "resumes", "jobs", "applications"]:
                for idx in indexes:
                    if idx['name'] != '_id_':  # Skip default _id index
                        keys = list(idx['key'].keys())
                        print(f"    └─ {idx['name']}: {', '.join(keys)}")
                        
        except Exception as e:
            print(f"  ❌ {collection_name}: Error - {e}")
    
    print(f"\n🎉 Index creation complete! Total indexes: {total_indexes}")
    print("\nIndexes are now optimized for:")
    print("  • Fast user authentication and lookups")
    print("  • Efficient resume and job searches")
    print("  • Quick application status queries")
    print("  • Analytics event aggregation")
    print("  • Real-time notification delivery")


if __name__ == "__main__":
    main()