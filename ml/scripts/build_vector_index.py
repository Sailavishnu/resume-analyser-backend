"""
Build FAISS Vector Index from MongoDB Jobs

This script:
1. Loads all active jobs from MongoDB
2. Generates embeddings for each job using Sentence-BERT
3. Builds a FAISS index for fast similarity search
4. Saves the index and metadata to disk

Usage:
    python ml/scripts/build_vector_index.py
    python ml/scripts/build_vector_index.py --rebuild  # Force rebuild
"""
import sys
import os
from pathlib import Path
import logging
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.db.mongodb import get_db
from app.db.collections import JOBS_COLLECTION
from app.ml.embeddings import embedding_service, get_job_embedding
from app.ml.vector_store import get_vector_store

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_index(rebuild: bool = False):
    """
    Build FAISS index from all active jobs in MongoDB.
    
    Args:
        rebuild: If True, rebuild even if index exists
    """
    logger.info("=" * 60)
    logger.info("Building FAISS Vector Index for Job Matching")
    logger.info("=" * 60)
    
    # Get vector store
    vector_store = get_vector_store()
    
    # Check if index already exists
    if vector_store.is_built() and not rebuild:
        logger.info("✓ Index already exists. Use --rebuild to force rebuild.")
        return
    
    if rebuild:
        logger.info("🔄 Rebuilding index (forced)...")
    else:
        logger.info("🏗️  Building new index...")
    
    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    db = get_db()
    jobs_collection = db[JOBS_COLLECTION]
    
    # Query active jobs
    logger.info("Fetching active jobs from database...")
    query = {"status": "active"}
    jobs = list(jobs_collection.find(query))
    
    if not jobs:
        logger.warning("⚠️  No active jobs found in database!")
        logger.info("Please add jobs to MongoDB first.")
        return
    
    logger.info(f"Found {len(jobs)} active jobs")
    
    # Generate embeddings and build index
    logger.info("Generating embeddings and building FAISS index...")
    logger.info("This may take a few minutes...")
    
    successful = 0
    failed = 0
    
    for idx, job in enumerate(jobs, 1):
        try:
            job_id = str(job["_id"])
            
            # Generate embedding
            embedding = get_job_embedding(job)
            
            # Prepare metadata
            metadata = {
                "job_id": job_id,
                "title": job.get("jobTitle") or job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "job_type": job.get("jobType") or job.get("job_type", ""),
                "status": job.get("status", "active")
            }
            
            # Add to index
            vector_store.add_job(job_id, embedding, metadata)
            successful += 1
            
            # Progress indicator
            if idx % 10 == 0 or idx == len(jobs):
                logger.info(f"  Progress: {idx}/{len(jobs)} jobs processed")
        
        except Exception as e:
            logger.error(f"  Failed to process job {job.get('_id')}: {e}")
            failed += 1
    
    # Save index to disk
    logger.info("Saving index to disk...")
    vector_store.save()
    
    # Summary
    logger.info("=" * 60)
    logger.info("✅ Index Build Complete!")
    logger.info(f"  Total jobs: {len(jobs)}")
    logger.info(f"  Successfully indexed: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Index size: {vector_store.size()} vectors")
    logger.info(f"  Index saved to: {vector_store.index_path}")
    logger.info("=" * 60)
    
    # Test the index
    logger.info("\n🧪 Testing index with sample query...")
    test_query(vector_store, jobs[0] if jobs else None)


def test_query(vector_store, sample_job):
    """
    Test the index with a sample query.
    """
    if not sample_job:
        logger.info("  No sample job available for testing")
        return
    
    try:
        # Use first job as test query
        test_embedding = get_job_embedding(sample_job)
        results = vector_store.search(test_embedding, top_k=5)
        
        logger.info(f"\n  Test query: '{sample_job.get('jobTitle') or sample_job.get('title')}'")
        logger.info(f"  Top 5 similar jobs:")
        
        for idx, (job_id, score, metadata) in enumerate(results, 1):
            logger.info(f"    {idx}. {metadata.get('title')} at {metadata.get('company')} (score: {score:.4f})")
        
        logger.info("  ✓ Index is working correctly!")
    
    except Exception as e:
        logger.error(f"  ⚠️  Test query failed: {e}")


def get_index_info():
    """
    Display information about the current index.
    """
    logger.info("=" * 60)
    logger.info("FAISS Index Information")
    logger.info("=" * 60)
    
    vector_store = get_vector_store()
    
    if not vector_store.is_built():
        logger.info("❌ No index found")
        logger.info("Run: python ml/scripts/build_vector_index.py")
        return
    
    logger.info(f"✓ Index exists")
    logger.info(f"  Location: {vector_store.index_path}")
    logger.info(f"  Size: {vector_store.size()} vectors")
    logger.info(f"  Dimension: 384 (Sentence-BERT)")
    logger.info(f"  Index type: FAISS IndexFlatIP (cosine similarity)")
    
    # Check metadata
    if os.path.exists(vector_store.metadata_path):
        import json
        with open(vector_store.metadata_path, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"  Jobs indexed: {len(metadata)}")
        
        # Sample metadata
        if metadata:
            sample_key = list(metadata.keys())[0]
            sample = metadata[sample_key]
            logger.info(f"\n  Sample job:")
            logger.info(f"    Title: {sample.get('title')}")
            logger.info(f"    Company: {sample.get('company')}")
            logger.info(f"    Location: {sample.get('location')}")
    
    logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build FAISS vector index from MongoDB jobs"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild even if index exists"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display index information"
    )
    
    args = parser.parse_args()
    
    try:
        if args.info:
            get_index_info()
        else:
            build_index(rebuild=args.rebuild)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Build interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Build failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
