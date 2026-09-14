"""
Resume management service - upload, analysis, versions, improvements.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List

from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError, StorageError
from app.services.cloudinary_service import CloudinaryService
from app.services.document_service import DocumentService
from app.utils.dates import utc_now
from app.utils.scoring import calculate_resume_health_score, calculate_ats_score
from app.utils.files import validate_resume_file, generate_unique_filename
from app.db import collections as C


class ResumeService:
    def __init__(self, db: Database):
        self.db = db
        self.cloudinary = CloudinaryService()
        self.document_service = DocumentService()
    
    async def upload_resume(
        self, 
        student_id: str, 
        file_content: bytes, 
        filename: str, 
        content_type: str,
        max_size_bytes: int
    ) -> Dict[str, Any]:
        """
        Upload and process a new resume.
        
        Returns the created resume document.
        """
        # Validate file
        validation = validate_resume_file(filename, content_type, len(file_content), max_size_bytes)
        if not validation['valid']:
            raise ValidationError(f"Invalid file: {', '.join(validation['errors'])}")
        
        # Generate unique filename
        unique_filename = generate_unique_filename(validation['sanitized_name'], f"student_{student_id}")
        
        try:
            # Upload to Cloudinary
            upload_result = self.cloudinary.upload_resume(file_content, unique_filename, student_id)
            
            # Mark existing resumes as not current
            self.db[C.RESUMES].update_many(
                {"student_id": ObjectId(student_id)},
                {"$set": {"is_current": False}}
            )
            
            # Create resume document
            resume_doc = {
                "student_id": ObjectId(student_id),
                "name": validation['sanitized_name'].split('.')[0],  # Remove extension
                "file_name": unique_filename,
                "file_type": content_type,
                "file_size": len(file_content),
                "cloudinary_public_id": upload_result['public_id'],
                "cloudinary_secure_url": upload_result['secure_url'],
                "version": 1,
                "is_current": True,
                "status": "uploaded",
                "analysis_status": "pending",
                "analysis_progress": 0,
                "analysis_stage": "Queued for processing",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            result = self.db[C.RESUMES].insert_one(resume_doc)
            resume_doc["_id"] = result.inserted_id
            
            # Start async analysis
            await self._analyze_resume_async(str(result.inserted_id), file_content, content_type)
            
            return resume_doc
            
        except Exception as e:
            # Clean up on failure
            if 'upload_result' in locals():
                self.cloudinary.delete_file(upload_result['public_id'])
            raise StorageError(f"Resume upload failed: {str(e)}")
    
    async def get_student_resumes(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all resumes for a student."""
        cursor = self.db[C.RESUMES].find(
            {"student_id": ObjectId(student_id)}
        ).sort("created_at", -1)
        
        resumes = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            resumes.append(doc)
        
        return resumes
    
    async def get_resume_by_id(self, resume_id: str, student_id: str = None) -> Dict[str, Any]:
        """
        Get resume by ID. Optionally verify ownership.
        """
        filter_dict = {"_id": ObjectId(resume_id)}
        if student_id:
            filter_dict["student_id"] = ObjectId(student_id)
        
        resume = self.db[C.RESUMES].find_one(filter_dict)
        if not resume:
            raise NotFoundError("Resume")
        
        resume["id"] = str(resume["_id"])
        return resume
    
    async def delete_resume(self, resume_id: str, student_id: str) -> None:
        """Delete resume and associated data."""
        resume = await self.get_resume_by_id(resume_id, student_id)
        
        # Delete from Cloudinary
        if resume.get("cloudinary_public_id"):
            self.cloudinary.delete_file(resume["cloudinary_public_id"])
        
        # Delete from database
        self.db[C.RESUMES].delete_one({"_id": ObjectId(resume_id)})
        self.db[C.RESUME_ANALYSES].delete_many({"resume_id": ObjectId(resume_id)})
        self.db[C.RESUME_IMPROVEMENTS].delete_many({"resume_id": ObjectId(resume_id)})
        self.db[C.RESUME_VERSIONS].delete_many({"resume_id": ObjectId(resume_id)})
    
    async def get_resume_analysis(self, resume_id: str, student_id: str = None) -> Dict[str, Any]:
        """Get latest analysis for resume."""
        # Verify access
        await self.get_resume_by_id(resume_id, student_id)
        
        analysis = self.db[C.RESUME_ANALYSES].find_one(
            {"resume_id": ObjectId(resume_id)},
            sort=[("created_at", -1)]
        )
        
        if not analysis:
            raise NotFoundError("Resume analysis not found")
        
        analysis["id"] = str(analysis["_id"])
        return analysis
    
    async def get_resume_improvements(self, resume_id: str, student_id: str = None) -> List[Dict[str, Any]]:
        """Get improvement suggestions for resume."""
        # Verify access
        await self.get_resume_by_id(resume_id, student_id)
        
        cursor = self.db[C.RESUME_IMPROVEMENTS].find(
            {"resume_id": ObjectId(resume_id)}
        ).sort("created_at", -1)
        
        improvements = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            improvements.append(doc)
        
        return improvements
    
    async def update_improvement_status(
        self, 
        improvement_id: str, 
        status: str, 
        student_id: str
    ) -> Dict[str, Any]:
        """Update improvement suggestion status (accept/reject)."""
        improvement = self.db[C.RESUME_IMPROVEMENTS].find_one({"_id": ObjectId(improvement_id)})
        if not improvement:
            raise NotFoundError("Improvement suggestion")
        
        # Verify ownership
        if str(improvement["student_id"]) != student_id:
            raise ForbiddenError("Not authorized to modify this improvement")
        
        # Update status
        self.db[C.RESUME_IMPROVEMENTS].update_one(
            {"_id": ObjectId(improvement_id)},
            {"$set": {"status": status, "updated_at": utc_now()}}
        )
        
        # If accepted, create new resume version
        if status == "accepted":
            await self._create_improved_version(improvement)
        
        improvement["status"] = status
        improvement["id"] = str(improvement["_id"])
        return improvement
    
    # ─── Private methods ───────────────────────────────────────────────────
    
    async def _analyze_resume_async(self, resume_id: str, file_content: bytes, content_type: str) -> None:
        """
        Analyze resume content and store results.
        In production, this would be a background task.
        """
        try:
            # Update status
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "status": "processing",
                    "analysis_progress": 20,
                    "analysis_stage": "Extracting text"
                }}
            )
            
            # Extract text
            raw_text = self.document_service.extract_text_from_bytes(file_content, content_type)
            
            # Update progress
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "analysis_progress": 50,
                    "analysis_stage": "Parsing structure"
                }}
            )
            
            # Parse structure
            parsed_data = self.document_service.parse_resume_structure(raw_text)
            
            # Update progress
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "analysis_progress": 75,
                    "analysis_stage": "Calculating scores"
                }}
            )
            
            # Calculate scores
            resume_health, section_scores = calculate_resume_health_score(parsed_data)
            ats_score, ats_checks = calculate_ats_score(parsed_data)
            
            # Store parsed data in resume
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {"parsed_data": parsed_data}}
            )
            
            # Create analysis record
            analysis_doc = {
                "resume_id": ObjectId(resume_id),
                "overall_score": resume_health,
                "ats_score": ats_score,
                "section_scores": section_scores,
                "strengths": self._generate_strengths(parsed_data, section_scores),
                "warnings": self._generate_warnings(parsed_data, section_scores),
                "critical_issues": [],
                "matched_keywords": [],
                "missing_keywords": [],
                "recommendations": self._generate_recommendations(parsed_data, section_scores),
                "analysis_version": "1.0",
                "created_at": utc_now(),
            }
            
            self.db[C.RESUME_ANALYSES].insert_one(analysis_doc)
            
            # Generate improvements
            await self._generate_improvements(resume_id, parsed_data, section_scores)
            
            # Update final status
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "status": "analyzed",
                    "analysis_status": "completed",
                    "analysis_progress": 100,
                    "analysis_stage": "Complete"
                }}
            )
            
        except Exception as e:
            # Mark as failed
            self.db[C.RESUMES].update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "status": "failed",
                    "analysis_status": "failed",
                    "analysis_stage": f"Failed: {str(e)}"
                }}
            )
    
    def _generate_strengths(self, parsed_data: dict, section_scores: dict) -> List[str]:
        """Generate list of resume strengths."""
        strengths = []
        
        if section_scores.get("skills", 0) >= 80:
            strengths.append("Strong technical skill diversity")
        
        if section_scores.get("projects", 0) >= 80:
            strengths.append("Excellent project portfolio")
        
        if section_scores.get("experience", 0) >= 70:
            strengths.append("Good professional experience")
        
        if parsed_data.get("summary") and len(parsed_data["summary"]) > 100:
            strengths.append("Comprehensive professional summary")
        
        return strengths
    
    def _generate_warnings(self, parsed_data: dict, section_scores: dict) -> List[str]:
        """Generate list of resume warnings."""
        warnings = []
        
        if section_scores.get("skills", 0) < 60:
            warnings.append("Limited technical skills listed")
        
        if not parsed_data.get("projects"):
            warnings.append("No projects mentioned")
        
        if not parsed_data.get("summary"):
            warnings.append("Missing professional summary")
        
        if section_scores.get("impact", 0) < 50:
            warnings.append("Lacks quantified achievements")
        
        return warnings
    
    def _generate_recommendations(self, parsed_data: dict, section_scores: dict) -> List[Dict[str, Any]]:
        """Generate improvement recommendations."""
        recommendations = []
        
        if section_scores.get("skills", 0) < 70:
            recommendations.append({
                "category": "skills",
                "priority": "high",
                "suggestion": "Add more relevant technical skills",
                "example": "Include frameworks, tools, and technologies you've used"
            })
        
        if not parsed_data.get("summary"):
            recommendations.append({
                "category": "summary",
                "priority": "high",
                "suggestion": "Add a professional summary",
                "example": "Brief overview of your expertise and career goals"
            })
        
        if section_scores.get("impact", 0) < 60:
            recommendations.append({
                "category": "impact",
                "priority": "medium",
                "suggestion": "Quantify your achievements",
                "example": "Use numbers, percentages, and metrics to show impact"
            })
        
        return recommendations
    
    async def _generate_improvements(self, resume_id: str, parsed_data: dict, section_scores: dict) -> None:
        """Generate specific improvement suggestions."""
        resume = self.db[C.RESUMES].find_one({"_id": ObjectId(resume_id)})
        student_id = resume["student_id"]
        
        improvements = []
        
        # Summary improvement
        if not parsed_data.get("summary") or len(parsed_data.get("summary", "")) < 50:
            improvements.append({
                "resume_id": ObjectId(resume_id),
                "student_id": student_id,
                "section": "summary",
                "original_text": parsed_data.get("summary", ""),
                "suggested_text": "Motivated Computer Science student with expertise in full-stack development and strong problem-solving skills. Experienced in modern web technologies and passionate about creating efficient, scalable solutions.",
                "reason": "A strong summary helps recruiters quickly understand your value proposition",
                "improvement_type": "professional",
                "status": "pending",
                "created_at": utc_now(),
            })
        
        # Insert improvements
        if improvements:
            self.db[C.RESUME_IMPROVEMENTS].insert_many(improvements)
    
    async def _create_improved_version(self, improvement: dict) -> None:
        """Create new resume version with accepted improvement."""
        # This would create a new version with the improvement applied
        # For now, just increment version number
        self.db[C.RESUME_VERSIONS].insert_one({
            "resume_id": improvement["resume_id"],
            "version_number": 2,  # Would calculate next version
            "target_role": None,
            "ats_score": None,
            "resume_health_score": None,
            "content": {"improvement_applied": str(improvement["_id"])},
            "created_at": utc_now(),
        })