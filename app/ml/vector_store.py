"""
FAISS Vector Database Manager

Manages semantic search index for jobs using FAISS (Facebook AI Similarity Search).
Supports adding, searching, and persisting job embeddings.
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
import faiss
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """
    FAISS-based vector store for semantic job search.
    
    Features:
    - Fast similarity search (L2 or cosine)
    - Persistent storage
    - Metadata storage (job IDs and details)
    - Batch operations
    """
    
    def __init__(self, embedding_dim: int = 384, index_type: str = "flat"):
        """
        Initialize vector store.
        
        Args:
            embedding_dim: Dimension of embedding vectors (384 for MiniLM)
            index_type: FAISS index type ('flat' for exact search, 'ivf' for approximate)
        """
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        
        # FAISS index
        self.index: Optional[faiss.Index] = None
        
        # Metadata storage (maps index position to job data)
        self.job_ids: List[str] = []  # Job IDs in order
        self.job_metadata: Dict[str, dict] = {}  # job_id -> job details
        
        # Initialize index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize FAISS index based on type."""
        if self.index_type == "flat":
            # Exact search using L2 distance (after normalization, equivalent to cosine)
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # IP = Inner Product
        elif self.index_type == "ivf":
            # Approximate search for larger datasets
            quantizer = faiss.IndexFlatIP(self.embedding_dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")
        
        logger.info(f"Initialized FAISS index: {self.index_type}, dim={self.embedding_dim}")
    
    def add_job(self, job_id: str, embedding: np.ndarray, metadata: dict):
        """
        Add a single job to the vector store.
        
        Args:
            job_id: Unique job identifier
            embedding: Job embedding vector (must be normalized)
            metadata: Job details (title, company, skills, etc.)
        """
        if job_id in self.job_metadata:
            logger.warning(f"Job {job_id} already exists. Skipping.")
            return
        
        # Ensure embedding is 2D for FAISS
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        # Add to FAISS index
        self.index.add(embedding.astype(np.float32))
        
        # Store metadata
        self.job_ids.append(job_id)
        self.job_metadata[job_id] = metadata
        
        logger.debug(f"Added job {job_id} to vector store")
    
    def add_jobs_batch(
        self, 
        job_ids: List[str], 
        embeddings: np.ndarray, 
        metadata_list: List[dict]
    ):
        """
        Add multiple jobs in batch (faster than individual adds).
        
        Args:
            job_ids: List of job IDs
            embeddings: Array of embeddings (num_jobs, embedding_dim)
            metadata_list: List of metadata dicts
        """
        if len(job_ids) != len(embeddings) or len(job_ids) != len(metadata_list):
            raise ValueError("Length mismatch between job_ids, embeddings, and metadata")
        
        # Filter out existing jobs
        new_jobs = []
        new_embeddings = []
        new_metadata = []
        
        for job_id, emb, meta in zip(job_ids, embeddings, metadata_list):
            if job_id not in self.job_metadata:
                new_jobs.append(job_id)
                new_embeddings.append(emb)
                new_metadata.append(meta)
        
        if not new_jobs:
            logger.info("No new jobs to add")
            return
        
        # Add to FAISS
        embeddings_array = np.array(new_embeddings, dtype=np.float32)
        self.index.add(embeddings_array)
        
        # Store metadata
        self.job_ids.extend(new_jobs)
        for job_id, meta in zip(new_jobs, new_metadata):
            self.job_metadata[job_id] = meta
        
        logger.info(f"Added {len(new_jobs)} jobs to vector store")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 10,
        filter_fn: Optional[callable] = None
    ) -> List[Tuple[str, float, dict]]:
        """
        Search for most similar jobs.
        
        Args:
            query_embedding: Resume embedding vector
            top_k: Number of top results to return
            filter_fn: Optional function to filter jobs (e.g., by location, type)
        
        Returns:
            List of (job_id, similarity_score, metadata) tuples, sorted by similarity
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Ensure query is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search in FAISS
        # We request more results than top_k to account for filtering
        search_k = min(top_k * 3, self.index.ntotal)
        distances, indices = self.index.search(
            query_embedding.astype(np.float32), 
            search_k
        )
        
        # Convert results to list of tuples
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # No more results
                break
            
            job_id = self.job_ids[idx]
            metadata = self.job_metadata[job_id]
            
            # Apply filter if provided
            if filter_fn and not filter_fn(metadata):
                continue
            
            # Distance is inner product (higher = more similar)
            similarity_score = float(dist)
            
            results.append((job_id, similarity_score, metadata))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def get_job_by_id(self, job_id: str) -> Optional[dict]:
        """Get job metadata by ID."""
        return self.job_metadata.get(job_id)
    
    def remove_job(self, job_id: str):
        """
        Remove a job from the store.
        
        Note: FAISS doesn't support deletion, so we mark as removed in metadata.
        For a clean rebuild, use rebuild_index().
        """
        if job_id in self.job_metadata:
            self.job_metadata[job_id]["_deleted"] = True
            logger.info(f"Marked job {job_id} as deleted")
        else:
            logger.warning(f"Job {job_id} not found")
    
    def rebuild_index(self):
        """
        Rebuild index excluding deleted jobs.
        
        This is necessary after deletions to reclaim space.
        """
        logger.info("Rebuilding vector index...")
        
        # Filter active jobs
        active_jobs = [
            (job_id, self.job_metadata[job_id]) 
            for job_id in self.job_ids 
            if not self.job_metadata[job_id].get("_deleted", False)
        ]
        
        if not active_jobs:
            logger.warning("No active jobs to rebuild")
            self._initialize_index()
            self.job_ids = []
            self.job_metadata = {}
            return
        
        # Re-encode all active jobs
        # This would require access to original job data - placeholder for now
        logger.warning("Full rebuild requires re-encoding. Not implemented yet.")
    
    def save(self, index_path: str, metadata_path: str):
        """
        Save index and metadata to disk.
        
        Args:
            index_path: Path to save FAISS index (.index file)
            metadata_path: Path to save metadata (.pkl file)
        """
        try:
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata = {
                "job_ids": self.job_ids,
                "job_metadata": self.job_metadata,
                "embedding_dim": self.embedding_dim,
                "index_type": self.index_type
            }
            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved vector store: {index_path}, {metadata_path}")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise
    
    def load(self, index_path: str, metadata_path: str):
        """
        Load index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata file
        """
        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
            
            self.job_ids = metadata["job_ids"]
            self.job_metadata = metadata["job_metadata"]
            self.embedding_dim = metadata["embedding_dim"]
            self.index_type = metadata["index_type"]
            
            logger.info(
                f"Loaded vector store with {len(self.job_ids)} jobs. "
                f"Index type: {self.index_type}, dim: {self.embedding_dim}"
            )
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            raise
    
    @property
    def size(self) -> int:
        """Get number of jobs in store (including deleted)."""
        return self.index.ntotal
    
    @property
    def active_size(self) -> int:
        """Get number of active (non-deleted) jobs."""
        return sum(
            1 for meta in self.job_metadata.values() 
            if not meta.get("_deleted", False)
        )
    
    def get_statistics(self) -> dict:
        """Get vector store statistics."""
        return {
            "total_jobs": self.size,
            "active_jobs": self.active_size,
            "deleted_jobs": self.size - self.active_size,
            "embedding_dim": self.embedding_dim,
            "index_type": self.index_type,
            "memory_size_mb": self.index.ntotal * self.embedding_dim * 4 / (1024 * 1024)  # Rough estimate
        }


# Global singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(embedding_dim: int = 384) -> VectorStore:
    """Get or create global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(embedding_dim=embedding_dim)
    return _vector_store


def load_vector_store(index_path: str, metadata_path: str) -> VectorStore:
    """Load vector store from disk."""
    global _vector_store
    _vector_store = VectorStore()
    _vector_store.load(index_path, metadata_path)
    return _vector_store
