"""
Job Description matching service using ML model.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any

from app.core.exceptions import NotFoundError, ProcessingError, ValidationError
from app.ml.predictor import predictor
from app.utils.dates import utc_now
from app.ml.scoring import analyze_skill_gap
from app.cloud import collections as C


class JDMatchService:
    def __init__(self, db: Database):
        self.db = db

    async def compare_resume_to_job_description(self, resume_id: str, student_id: str, job_description: str) -> Dict[str, Any]:
        """Compare a saved resume with the skills and language in a supplied JD."""
        resume = self.db[C.RESUMES].find_one({
            "_id": ObjectId(resume_id),
            "student_id": ObjectId(student_id),
        })
        if not resume:
            raise NotFoundError("Resume not found or access denied")

        parsed = resume.get("parsed_data") or {}
        resume_skills = []
        for values in (parsed.get("skills") or {}).values():
            if isinstance(values, list):
                resume_skills.extend(value for value in values if isinstance(value, str))
        resume_skills.extend((parsed.get("nlp") or {}).get("normalized_skills") or [])
        resume_skills = list(dict.fromkeys(resume_skills))

        from app.ml.nlp_processor import nlp_processor
        job_skills = sorted(nlp_processor.extract_skills(job_description))
        if not job_skills:
            raise ValidationError("No supported technical skills were found in the job description. Include named technologies or tools.")

        skill_gap = analyze_skill_gap(resume_skills, job_skills)
        resume_text = parsed.get("raw_text") or " ".join(resume_skills)

        def semantic_score():
            from app.ml.embeddings import embedding_service
            resume_vector = embedding_service.encode_text(resume_text[:12000])
            job_vector = embedding_service.encode_text(job_description[:12000])
            similarity = embedding_service.calculate_similarity(resume_vector, job_vector)
            return round(similarity, 4), embedding_service.engine_name

        import asyncio
        similarity, engine = await asyncio.to_thread(semantic_score)
        return {
            "resume_id": resume_id,
            "skills_found_in_job_description": job_skills,
            "matched_skills": skill_gap["matched_skills"],
            "partial_skills": skill_gap["partial_skills"],
            "missing_skills": skill_gap["missing_skills"],
            "skill_coverage": round(skill_gap["skill_coverage"], 1),
            "semantic_similarity": similarity,
            "embedding_engine": engine,
        }
    
    async def calculate_match_score(self, resume_id: str, job_id: str, student_id: str) -> Dict[str, Any]:
        """
        Calculate resume-job match using ML model and store result.
        
        Returns the match result document.
        """
        # Verify resume ownership
        resume = self.db[C.RESUMES].find_one({
            "_id": ObjectId(resume_id),
            "student_id": ObjectId(student_id)
        })
        if not resume:
            raise NotFoundError("Resume not found or access denied")
        
        # Get job
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        
        # Check if match already exists (return cached if recent)
        existing_match = self.db[C.JOB_MATCHES].find_one({
            "student_id": ObjectId(student_id),
            "resume_id": ObjectId(resume_id),
            "job_id": ObjectId(job_id)
        })
        
        if existing_match:
            # Return existing if less than 24 hours old
            age_hours = (utc_now() - existing_match["created_at"]).total_seconds() / 3600
            if age_hours < 24:
                existing_match["id"] = str(existing_match["_id"])
                return existing_match
        
        try:
            # Ensure ML model is loaded
            if not predictor.is_loaded:
                predictor.load_model()
            
            # Get prediction from ML model
            prediction_result = predictor.predict_match_score(resume, job)
            
            # Extract resume skills for gap analysis
            parsed_data = resume.get("parsed_data", {})
            resume_skills = []
            skills_obj = parsed_data.get("skills", {})
            for category in skills_obj.values():
                if isinstance(category, list):
                    resume_skills.extend(category)
            
            # Analyze skill gap
            skill_analysis = analyze_skill_gap(
                resume_skills, 
                job.get("required_skills", []),
                job.get("preferred_skills", [])
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                skill_analysis, 
                parsed_data,
                job
            )
            
            # Create match document
            match_doc = {
                "student_id": ObjectId(student_id),
                "resume_id": ObjectId(resume_id),
                "job_id": ObjectId(job_id),
                "model_version": prediction_result["model_version"],
                "overall_score": prediction_result["overall_score"],
                "display_score": prediction_result["display_score"],
                "features": prediction_result["features"],
                "matched_skills": skill_analysis["matched_skills"],
                "partial_skills": skill_analysis.get("partial_skills", []),
                "missing_skills": skill_analysis["missing_skills"],
                "recommendations": recommendations,
                "created_at": utc_now(),
            }
            
            # Store or update match
            if existing_match:
                self.db[C.JOB_MATCHES].update_one(
                    {"_id": existing_match["_id"]},
                    {"$set": match_doc}
                )
                match_doc["_id"] = existing_match["_id"]
            else:
                result = self.db[C.JOB_MATCHES].insert_one(match_doc)
                match_doc["_id"] = result.inserted_id
            
            match_doc["id"] = str(match_doc["_id"])
            return match_doc
            
        except Exception as e:
            raise ProcessingError(f"Match calculation failed: {str(e)}")
    
    async def get_match_by_id(self, match_id: str) -> Dict[str, Any]:
        """Get match result by ID."""
        match = self.db[C.JOB_MATCHES].find_one({"_id": ObjectId(match_id)})
        if not match:
            raise NotFoundError("Job match")
        
        match["id"] = str(match["_id"])
        return match
    
    async def get_student_matches(self, student_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        """Get recent matches for student."""
        cursor = self.db[C.JOB_MATCHES].find(
            {"student_id": ObjectId(student_id)}
        ).sort("created_at", -1).limit(limit)
        
        matches = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            matches.append(doc)
        
        return matches
    
    def _generate_recommendations(
        self, 
        skill_analysis: dict, 
        parsed_data: dict,
        job: dict
    ) -> list[str]:
        """Generate actionable recommendations based on match analysis."""
        recommendations = []
        
        # Skill recommendations
        missing_skills = skill_analysis.get("missing_skills", [])
        if missing_skills:
            if len(missing_skills) <= 3:
                recommendations.append(
                    f"Learn {', '.join(missing_skills[:3])} to strengthen your application"
                )
            else:
                recommendations.append(
                    f"Focus on learning {missing_skills[0]} and {missing_skills[1]} as priority skills"
                )
        
        # Experience recommendations
        job_min_exp = job.get("experience_min", 0)
        user_experience = len(parsed_data.get("experience", []))
        
        if user_experience == 0 and job_min_exp > 0:
            recommendations.append("Consider applying for internships to gain relevant experience")
        
        # Project recommendations
        user_projects = len(parsed_data.get("projects", []))
        if user_projects < 2:
            recommendations.append("Build more projects showcasing the required skills")
        
        # Education alignment
        job_title = job.get("title", "").lower()
        if "senior" in job_title or "lead" in job_title:
            recommendations.append("Consider gaining more experience before applying to senior roles")
        
        return recommendations[:4]  # Limit to top 4 recommendations
