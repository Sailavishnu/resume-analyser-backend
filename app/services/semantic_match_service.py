"""
Semantic Job Matching Service

High-level service that combines traditional ML matching with semantic search
using embeddings, vector database, and NLP processing.
"""
from typing import List, Dict, Optional, Tuple
from bson import ObjectId
import logging

from app.db.mongodb import get_db
from app.db.collections import JOBS_COLLECTION, RESUMES_COLLECTION
from app.ml.embeddings import embedding_service, get_resume_embedding, get_job_embedding
from app.ml.vector_store import get_vector_store
from app.ml.predictor import predictor
from app.ml.feature_extractor import ResumeJobFeatureExtractor
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class SemanticMatchService:
    """
    Service for semantic job matching using vector search and NLP.
    
    Combines:
    - Traditional ML model (RandomForest with 6 features)
    - Semantic similarity (Sentence-BERT embeddings)
    - Vector search (FAISS)
    - Hybrid scoring
    """
    
    def __init__(self):
        self.db = get_db()
        self.feature_extractor_traditional = ResumeJobFeatureExtractor(use_semantic=False)
        self.feature_extractor_hybrid = ResumeJobFeatureExtractor(use_semantic=True)
    
    def find_matching_jobs_semantic(
        self,
        resume_id: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Find matching jobs using semantic search.
        
        Args:
            resume_id: MongoDB resume ID
            top_k: Number of top matches to return
            filters: Optional filters (location, job_type, etc.)
        
        Returns:
            List of job matches with scores
        """
        # Get resume data
        resume = self.db[RESUMES_COLLECTION].find_one({"_id": ObjectId(resume_id)})
        if not resume:
            raise NotFoundError(f"Resume {resume_id} not found")
        
        parsed_data = resume.get("parsedData") or resume.get("parsed_data")
        if not parsed_data:
            raise ValidationError("Resume has not been parsed yet")
        
        # Generate resume embedding
        try:
            resume_embedding = get_resume_embedding(parsed_data)
        except Exception as e:
            logger.error(f"Failed to generate resume embedding: {e}")
            raise ValidationError("Failed to process resume for semantic search")
        
        # Search vector store
        vector_store = get_vector_store()
        
        # Apply filters
        def filter_fn(job_meta):
            if not filters:
                return True
            
            if filters.get("location") and job_meta.get("location") != filters["location"]:
                return False
            if filters.get("job_type") and job_meta.get("job_type") != filters["job_type"]:
                return False
            if filters.get("status") != job_meta.get("status", "active"):
                return True  # Only active jobs by default
            
            return True
        
        # Get semantic matches
        semantic_matches = vector_store.search(
            resume_embedding,
            top_k=top_k * 2,  # Get more to account for filtering
            filter_fn=filter_fn
        )
        
        # Enhance with ML predictions and detailed scoring
        results = []
        for job_id, semantic_score, job_metadata in semantic_matches[:top_k]:
            # Get full job details from DB
            job = self.db[JOBS_COLLECTION].find_one({"_id": ObjectId(job_id)})
            if not job:
                continue
            
            # Calculate hybrid score
            try:
                hybrid_score = self._calculate_hybrid_score(
                    parsed_data,
                    job,
                    semantic_score,
                    resume_embedding
                )
            except Exception as e:
                logger.warning(f"Failed to calculate hybrid score for job {job_id}: {e}")
                hybrid_score = {
                    "overall_score": semantic_score * 100,
                    "semantic_score": semantic_score * 100,
                    "ml_score": None,
                    "match_type": "semantic_only"
                }
            
            # Build result
            result = {
                "job_id": str(job["_id"]),
                "job_title": job.get("jobTitle") or job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "job_type": job.get("jobType") or job.get("job_type"),
                "salary_range": f"{job.get('salary_min', 0)}-{job.get('salary_max', 0)}",
                "scores": hybrid_score,
                "required_skills": job.get("requiredSkills") or job.get("required_skills", []),
                "match_details": self._generate_match_explanation(
                    parsed_data, 
                    job, 
                    hybrid_score
                )
            }
            
            results.append(result)
        
        # Sort by overall score
        results.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
        
        return results
    
    def calculate_semantic_match_score(
        self,
        resume_id: str,
        job_id: str
    ) -> Dict:
        """
        Calculate detailed semantic match score between resume and job.
        
        Returns:
            Dictionary with scores and match details
        """
        # Get resume
        resume = self.db[RESUMES_COLLECTION].find_one({"_id": ObjectId(resume_id)})
        if not resume:
            raise NotFoundError(f"Resume {resume_id} not found")
        
        parsed_data = resume.get("parsedData") or resume.get("parsed_data")
        
        # Get job
        job = self.db[JOBS_COLLECTION].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError(f"Job {job_id} not found")
        
        # Generate embeddings
        resume_embedding = get_resume_embedding(parsed_data)
        job_embedding = get_job_embedding(job)
        
        # Calculate semantic similarity
        semantic_score = float(embedding_service.calculate_similarity(
            resume_embedding,
            job_embedding
        ))
        
        # Calculate hybrid score
        hybrid_score = self._calculate_hybrid_score(
            parsed_data,
            job,
            semantic_score,
            resume_embedding,
            job_embedding
        )
        
        # Generate detailed explanation
        match_details = self._generate_match_explanation(parsed_data, job, hybrid_score)
        
        return {
            "resume_id": resume_id,
            "job_id": job_id,
            "scores": hybrid_score,
            "match_details": match_details,
            "job_info": {
                "title": job.get("jobTitle") or job.get("title"),
                "company": job.get("company"),
                "location": job.get("location")
            }
        }
    
    def _calculate_hybrid_score(
        self,
        resume_data: Dict,
        job_data: Dict,
        semantic_score: float,
        resume_embedding: Optional = None,
        job_embedding: Optional = None
    ) -> Dict:
        """
        Calculate hybrid score combining semantic + ML predictions.
        
        Returns:
            Dictionary with different score components
        """
        # Semantic score (already computed)
        semantic_score_pct = semantic_score * 100
        
        # Try ML prediction
        ml_score_pct = None
        if predictor.is_loaded:
            try:
                # Use traditional features for ML model (trained on those)
                features = self.feature_extractor_traditional.extract_features(
                    resume_data,
                    job_data
                )
                ml_score = predictor.predict_match_score(features)
                ml_score_pct = ml_score * 100
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        # Calculate overall score (weighted combination)
        if ml_score_pct is not None:
            # Hybrid: 60% semantic + 40% ML
            overall_score = (semantic_score_pct * 0.6) + (ml_score_pct * 0.4)
            match_type = "hybrid"
        else:
            # Semantic only
            overall_score = semantic_score_pct
            match_type = "semantic_only"
        
        return {
            "overall_score": round(overall_score, 2),
            "semantic_score": round(semantic_score_pct, 2),
            "ml_score": round(ml_score_pct, 2) if ml_score_pct else None,
            "match_type": match_type,
            "weights": {
                "semantic": 0.6 if match_type == "hybrid" else 1.0,
                "ml": 0.4 if match_type == "hybrid" else 0.0
            }
        }
    
    def _generate_match_explanation(
        self,
        resume_data: Dict,
        job_data: Dict,
        scores: Dict
    ) -> Dict:
        """
        Generate human-readable match explanation.
        """
        from app.utils.scoring import analyze_skill_gap
        
        # Skill analysis
        resume_skills = []
        skills_obj = resume_data.get("skills", {})
        for category in ["languages", "frameworks", "databases", "tools"]:
            resume_skills.extend(skills_obj.get(category, []))
        
        required_skills = job_data.get("requiredSkills") or job_data.get("required_skills", [])
        preferred_skills = job_data.get("preferredSkills") or job_data.get("preferred_skills", [])
        
        skill_gap = analyze_skill_gap(resume_skills, required_skills, preferred_skills)
        
        # Experience match
        experience_list = resume_data.get("experience", [])
        total_exp_years = len(experience_list)  # Simplified
        
        required_exp = job_data.get("minimumExperience") or job_data.get("experience_min", 0)
        
        experience_match = "Good match" if total_exp_years >= required_exp else "Below required"
        
        # Education match
        education_list = resume_data.get("education", [])
        has_degree = len(education_list) > 0
        
        return {
            "skill_gap": skill_gap,
            "experience_match": experience_match,
            "education_match": "Meets requirements" if has_degree else "Education info needed",
            "matching_skills": skill_gap.get("matched_skills", []),
            "missing_skills": skill_gap.get("missing_required", []),
            "score_breakdown": {
                "semantic_similarity": f"{scores['semantic_score']}% - Based on AI understanding of resume and job description",
                "ml_prediction": f"{scores.get('ml_score', 'N/A')}% - Based on traditional feature matching" if scores.get('ml_score') else "ML model not available",
                "overall": f"{scores['overall_score']}% - Combined score"
            }
        }
    
    def search_jobs_by_skills(
        self,
        skills: List[str],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search jobs by skill list (without full resume).
        
        Useful for quick skill-based search.
        """
        # Create a minimal "resume" with just skills
        temp_resume = {
            "skills": {
                "languages": skills[:5],
                "frameworks": skills[5:10] if len(skills) > 5 else [],
                "tools": skills[10:] if len(skills) > 10 else []
            },
            "summary": f"Professional with skills in {', '.join(skills[:5])}"
        }
        
        # Generate embedding
        embedding = get_resume_embedding(temp_resume)
        
        # Search
        vector_store = get_vector_store()
        matches = vector_store.search(embedding, top_k=top_k)
        
        # Format results
        results = []
        for job_id, score, metadata in matches:
            job = self.db[JOBS_COLLECTION].find_one({"_id": ObjectId(job_id)})
            if job:
                results.append({
                    "job_id": str(job["_id"]),
                    "job_title": job.get("jobTitle") or job.get("title"),
                    "company": job.get("company"),
                    "semantic_score": round(score * 100, 2),
                    "required_skills": job.get("requiredSkills") or job.get("required_skills", [])
                })
        
        return results


# Global service instance
_semantic_match_service = None


def get_semantic_match_service() -> SemanticMatchService:
    """Get or create semantic match service instance."""
    global _semantic_match_service
    if _semantic_match_service is None:
        _semantic_match_service = SemanticMatchService()
    return _semantic_match_service
