"""
FAISS Vector Database Manager

Manages semantic search index for jobs using FAISS (Facebook AI Similarity Search).
Supports adding, searching, and persisting job embeddings.
"""
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pickle
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ENABLE_FAISS = os.environ.get("ENABLE_FAISS", "false").lower() in ("true", "1")
FAISS_AVAILABLE = False
faiss = None

if ENABLE_FAISS:
    try:
        import faiss
        FAISS_AVAILABLE = True
    except Exception as e:
        logger.warning(f"FAISS not available or blocked by system policy ({e}). Using NumPy vector search.")


class VectorStore:
    """
    Resilient Vector Store for semantic job search.
    Supports FAISS when available, with an automatic, zero-dependency 
    pure-NumPy fallback (immune to Windows Security DLL blocks).
    """
    
    def __init__(
        self, 
        embedding_dim: int = 384, 
        index_type: str = "flat",
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None
    ):
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        
        backend_root = Path(__file__).resolve().parent.parent.parent
        artifacts_dir = backend_root / "ml" / "artifacts"
        self.index_path = str(index_path or (artifacts_dir / "job_vectors.index"))
        self.metadata_path = str(metadata_path or (artifacts_dir / "job_vectors.pkl"))
        self.npy_path = str(artifacts_dir / "job_vectors.npy")
        
        # FAISS index (optional) and NumPy matrix storage
        self.index: Optional[Any] = None
        self.vectors: np.ndarray = np.empty((0, self.embedding_dim), dtype=np.float32)
        
        # Metadata storage (maps index position to job data)
        self.job_ids: List[str] = []  # Job IDs in order
        self.job_metadata: Dict[str, dict] = {}  # job_id -> job details
        
        # Initialize index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize FAISS index if available."""
        if FAISS_AVAILABLE and faiss is not None:
            try:
                if self.index_type == "flat":
                    self.index = faiss.IndexFlatIP(self.embedding_dim)
                elif self.index_type == "ivf":
                    quantizer = faiss.IndexFlatIP(self.embedding_dim)
                    self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
                logger.info(f"Initialized FAISS index: {self.index_type}, dim={self.embedding_dim}")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize FAISS index ({e}). Using NumPy.")
        
        self.index = None
        logger.info(f"Initialized NumPy vector engine: dim={self.embedding_dim}")
    
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
        
        # Ensure embedding is 2D
        emb_2d = embedding.reshape(1, -1).astype(np.float32) if embedding.ndim == 1 else embedding.astype(np.float32)
        
        # Add to vectors
        if len(self.vectors) == 0:
            self.vectors = emb_2d
        else:
            self.vectors = np.vstack([self.vectors, emb_2d])

        # Add to FAISS index if available
        if self.index is not None:
            try:
                self.index.add(emb_2d)
            except Exception as e:
                logger.warning(f"FAISS add warning: {e}")
        
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
        
        embeddings_array = np.array(new_embeddings, dtype=np.float32)
        if len(self.vectors) == 0:
            self.vectors = embeddings_array
        else:
            self.vectors = np.vstack([self.vectors, embeddings_array])

        # Add to FAISS if available
        if self.index is not None:
            try:
                self.index.add(embeddings_array)
            except Exception as e:
                logger.warning(f"FAISS batch add warning: {e}")
        
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
        total_items = len(self.vectors) if self.index is None else self.index.ntotal
        if total_items == 0:
            logger.warning("Vector store is empty")
            return []
        
        search_k = min(top_k * 3, total_items)
        flat_query = query_embedding.flatten().astype(np.float32)
        
        if self.index is not None:
            distances, indices = self.index.search(flat_query.reshape(1, -1), search_k)
            pairs = zip(distances[0], indices[0])
        else:
            scores = np.dot(self.vectors, flat_query)
            top_idx = np.argsort(scores)[::-1][:search_k]
            pairs = zip(scores[top_idx], top_idx)
        
        # Convert results to list of tuples
        results = []
        for dist, idx in pairs:
            if idx == -1 or idx >= len(self.job_ids):
                break
            
            job_id = self.job_ids[idx]
            metadata = self.job_metadata.get(job_id, {})
            
            # Apply filter if provided
            if filter_fn and not filter_fn(metadata):
                continue
            
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
    
    def is_built(self) -> bool:
        """Check if vector index contains indexed data or files exist."""
        if self.index is not None and self.index.ntotal > 0:
            return True
        if Path(self.index_path).exists() and Path(self.metadata_path).exists():
            try:
                self.load()
                return self.index is not None and self.index.ntotal > 0
            except Exception:
                return False
        return False

    def save(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """
        Save index and metadata to disk.
        
        Args:
            index_path: Path to save FAISS index (.index file)
            metadata_path: Path to save metadata (.pkl file)
        """
        target_index_path = index_path or self.index_path
        target_metadata_path = metadata_path or self.metadata_path
        try:
            Path(target_index_path).parent.mkdir(parents=True, exist_ok=True)
            Path(target_metadata_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index if available
            if FAISS_AVAILABLE and faiss is not None and self.index is not None:
                try:
                    faiss.write_index(self.index, target_index_path)
                except Exception as e:
                    logger.warning(f"FAISS write warning: {e}")
            
            if len(self.vectors) > 0:
                np.save(self.npy_path, self.vectors)
            
            # Save metadata
            metadata = {
                "job_ids": self.job_ids,
                "job_metadata": self.job_metadata,
                "embedding_dim": self.embedding_dim,
                "index_type": self.index_type
            }
            with open(target_metadata_path, "wb") as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved vector store: {target_index_path}, {target_metadata_path}")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise
    
    def load(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """
        Load index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata file
        """
        target_index_path = index_path or self.index_path
        target_metadata_path = metadata_path or self.metadata_path
        
        if not Path(target_metadata_path).exists():
            logger.info(f"Vector store metadata not found at {target_metadata_path}")
            return False
            
        try:
            # Load FAISS index if available and allowed
            if FAISS_AVAILABLE and faiss is not None and Path(target_index_path).exists():
                try:
                    self.index = faiss.read_index(target_index_path)
                except Exception as faiss_err:
                    logger.warning(f"Could not load FAISS index file ({faiss_err}). Falling back to NumPy.")
                    self.index = None
            else:
                self.index = None

            # Load NumPy vectors if available
            if Path(self.npy_path).exists():
                self.vectors = np.load(self.npy_path)

            # Load metadata
            with open(target_metadata_path, "rb") as f:
                metadata = pickle.load(f)
            
            self.job_ids = metadata["job_ids"]
            self.job_metadata = metadata["job_metadata"]
            self.embedding_dim = metadata["embedding_dim"]
            self.index_type = metadata["index_type"]
            
            logger.info(
                f"Loaded vector store with {len(self.job_ids)} jobs. "
                f"Engine: {'FAISS' if self.index is not None else 'NumPy'}, dim: {self.embedding_dim}"
            )
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            raise
    
    def size(self) -> int:
        """Get number of jobs in store (including deleted)."""
        return self.index.ntotal if self.index is not None else 0
    
    @property
    def active_size(self) -> int:
        """Get number of active (non-deleted) jobs."""
        return sum(
            1 for meta in self.job_metadata.values() 
            if not meta.get("_deleted", False)
        )
    
    def get_statistics(self) -> dict:
        """Get vector store statistics."""
        current_size = self.size()
        return {
            "total_jobs": current_size,
            "active_jobs": self.active_size,
            "deleted_jobs": current_size - self.active_size,
            "embedding_dim": self.embedding_dim,
            "index_type": self.index_type,
            "memory_size_mb": current_size * self.embedding_dim * 4 / (1024 * 1024)  # Rough estimate
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
