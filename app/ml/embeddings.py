"""
Sentence-BERT Embedding Generation Service

Generates semantic embeddings for resumes and job descriptions
using pre-trained sentence transformers for similarity matching.
"""
from typing import List, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating semantic embeddings.
    
    Uses 'all-MiniLM-L6-v2' model:
    - 384 dimensional embeddings
    - Fast inference (~500 sentences/sec on CPU)
    - Good balance of speed and quality
    - 80MB model size
    """
    
    _instance = None
    _model: Optional[SentenceTransformer] = None
    _model_name = "sentence-transformers/all-MiniLM-L6-v2"
    _embedding_dim = 384
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self):
        """Load the sentence transformer model."""
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info(f"Embedding model loaded successfully. Dimension: {self._embedding_dim}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_dim
    
    def encode_text(
        self, 
        text: Union[str, List[str]], 
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            text: Single text string or list of texts
            normalize: Whether to L2-normalize embeddings (recommended for cosine similarity)
            show_progress: Show progress bar for batch encoding
        
        Returns:
            numpy array of shape (embedding_dim,) for single text
            or (num_texts, embedding_dim) for multiple texts
        """
        if not self.is_loaded:
            raise RuntimeError("Embedding model not loaded. Call load_model() first.")
        
        if not text:
            raise ValueError("Text input cannot be empty")
        
        # Handle single string vs list
        is_single = isinstance(text, str)
        if is_single:
            text = [text]
        
        try:
            embeddings = self._model.encode(
                text,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )
            
            # Return single vector for single input
            if is_single:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise
    
    def encode_resume(self, resume_data: dict) -> np.ndarray:
        """
        Generate semantic embedding for a resume.
        
        Combines multiple resume sections into a rich text representation
        for better semantic matching.
        
        Args:
            resume_data: Dictionary with resume fields (from parsedData)
        
        Returns:
            384-dimensional embedding vector
        """
        text_parts = []
        
        # Summary (most important)
        if resume_data.get("summary"):
            text_parts.append(f"Summary: {resume_data['summary']}")
        
        # Skills
        skills = resume_data.get("skills", {})
        all_skills = []
        for skill_category in ["languages", "frameworks", "databases", "tools", "concepts"]:
            if skills.get(skill_category):
                all_skills.extend(skills[skill_category])
        
        if all_skills:
            text_parts.append(f"Skills: {', '.join(all_skills)}")
        
        # Projects (titles and descriptions)
        projects = resume_data.get("projects", [])
        for project in projects[:3]:  # Top 3 projects
            if project.get("projectName"):
                project_text = f"Project: {project['projectName']}"
                if project.get("description"):
                    project_text += f" - {project['description']}"
                text_parts.append(project_text)
        
        # Experience
        experience = resume_data.get("experience", [])
        for exp in experience[:2]:  # Top 2 experiences
            if exp.get("position"):
                exp_text = f"Experience: {exp['position']}"
                if exp.get("company"):
                    exp_text += f" at {exp['company']}"
                if exp.get("description"):
                    exp_text += f" - {exp['description']}"
                text_parts.append(exp_text)
        
        # Education
        education = resume_data.get("education", [])
        for edu in education[:1]:  # Most recent education
            if edu.get("degree") and edu.get("field"):
                text_parts.append(f"Education: {edu['degree']} in {edu['field']}")
        
        # Combine all parts
        combined_text = " | ".join(text_parts)
        
        if not combined_text:
            raise ValueError("Resume data is empty or invalid")
        
        return self.encode_text(combined_text, normalize=True)
    
    def encode_job(self, job_data: dict) -> np.ndarray:
        """
        Generate semantic embedding for a job description.
        
        Args:
            job_data: Dictionary with job fields
        
        Returns:
            384-dimensional embedding vector
        """
        text_parts = []
        
        # Job title (very important)
        if job_data.get("jobTitle") or job_data.get("title"):
            title = job_data.get("jobTitle") or job_data.get("title")
            text_parts.append(f"Position: {title}")
        
        # Description
        if job_data.get("description"):
            text_parts.append(f"Description: {job_data['description']}")
        
        # Required skills
        required_skills = job_data.get("requiredSkills", []) or job_data.get("required_skills", [])
        if required_skills:
            text_parts.append(f"Required Skills: {', '.join(required_skills)}")
        
        # Preferred skills
        preferred_skills = job_data.get("preferredSkills", []) or job_data.get("preferred_skills", [])
        if preferred_skills:
            text_parts.append(f"Preferred Skills: {', '.join(preferred_skills)}")
        
        # Responsibilities
        responsibilities = job_data.get("responsibilities", [])
        if responsibilities:
            resp_text = "; ".join(responsibilities[:3])  # Top 3 responsibilities
            text_parts.append(f"Responsibilities: {resp_text}")
        
        # Experience requirements
        if job_data.get("experienceNeeded"):
            text_parts.append(f"Experience: {job_data['experienceNeeded']}")
        
        # Education requirements
        if job_data.get("educationRequired"):
            text_parts.append(f"Education: {job_data['educationRequired']}")
        
        # Combine all parts
        combined_text = " | ".join(text_parts)
        
        if not combined_text:
            raise ValueError("Job data is empty or invalid")
        
        return self.encode_text(combined_text, normalize=True)
    
    def calculate_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        # Cosine similarity = dot product of normalized vectors
        similarity = np.dot(embedding1, embedding2)
        
        # Convert to 0-1 scale for easier interpretation
        # (0.5 + similarity/2) maps [-1, 1] to [0, 1]
        return float(similarity)
    
    def batch_similarity(
        self, 
        query_embedding: np.ndarray, 
        candidate_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between one query and multiple candidates.
        
        Args:
            query_embedding: Single embedding vector (embedding_dim,)
            candidate_embeddings: Multiple embeddings (num_candidates, embedding_dim)
        
        Returns:
            Array of similarity scores (num_candidates,)
        """
        # Matrix multiplication for batch cosine similarity
        similarities = np.dot(candidate_embeddings, query_embedding)
        return similarities


# Global singleton instance
embedding_service = EmbeddingService()


# Convenience functions
def load_embedding_model():
    """Load the embedding model (call on startup)."""
    embedding_service.load_model()


def get_resume_embedding(resume_data: dict) -> np.ndarray:
    """Generate embedding for a resume."""
    return embedding_service.encode_resume(resume_data)


def get_job_embedding(job_data: dict) -> np.ndarray:
    """Generate embedding for a job description."""
    return embedding_service.encode_job(job_data)


def calculate_semantic_similarity(resume_data: dict, job_data: dict) -> float:
    """
    Calculate semantic similarity between resume and job.
    
    Returns:
        Similarity score between -1 and 1
    """
    resume_emb = get_resume_embedding(resume_data)
    job_emb = get_job_embedding(job_data)
    return embedding_service.calculate_similarity(resume_emb, job_emb)
