"""
Resume management service - upload, analysis, versions, improvements.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List

from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError, StorageError, ProcessingError
from app.cloud.cloudinary_service import CloudinaryService
from app.ml.document_service import DocumentService
from app.utils.dates import utc_now
from app.ml.scoring import calculate_resume_health_score, calculate_ats_score
from app.utils.files import validate_resume_file, generate_unique_filename
from app.cloud import collections as C


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
        max_size_bytes: int,
        slot: str = "primary"
    ) -> Dict[str, Any]:
        """
        Upload and process a new resume to Firebase Storage + MongoDB.
        Supports 2-slot vault (primary / secondary).
        """
        # Validate file
        validation = validate_resume_file(filename, content_type, len(file_content), max_size_bytes)
        if not validation['valid']:
            raise ValidationError(f"Invalid file: {', '.join(validation['errors'])}")
        if slot not in ("primary", "secondary"):
            raise ValidationError("Slot must be 'primary' or 'secondary'")
        
        # Generate unique filename
        unique_filename = generate_unique_filename(validation['sanitized_name'], f"student_{student_id}")
        
        try:
            # Upload to Cloudinary as raw resource under resumes/{student_id}/
            upload_result = self.cloudinary.upload_resume(file_content, unique_filename, content_type, student_id)
            
            # If uploaded as primary, demote existing primary to secondary
            if slot == "primary":
                existing_secondaries = list(self.db[C.RESUMES].find(
                    {"student_id": ObjectId(student_id), "slot": "secondary"}
                ))
                for existing_secondary in existing_secondaries:
                    if existing_secondary.get("cloudinary_public_id"):
                        self.cloudinary.delete_file(existing_secondary["cloudinary_public_id"])
                    self.db[C.RESUMES].delete_one({"_id": existing_secondary["_id"]})
                    
                self.db[C.RESUMES].update_many(
                    {"student_id": ObjectId(student_id), "slot": "primary"},
                    {"$set": {"slot": "secondary", "is_primary": False, "is_current": False}}
                )
            elif slot == "secondary":
                # Remove every legacy duplicate so the vault remains capped at one per slot.
                for old_resume in self.db[C.RESUMES].find(
                    {"student_id": ObjectId(student_id), "slot": "secondary"}
                ):
                    if old_resume.get("cloudinary_public_id"):
                        self.cloudinary.delete_file(old_resume["cloudinary_public_id"])
                    self.db[C.RESUMES].delete_one({"_id": old_resume["_id"]})
            
            # Create resume document with Cloudinary metadata
            resume_doc = {
                "student_id": ObjectId(student_id),
                "name": validation['sanitized_name'].split('.')[0],
                "original_file_name": validation['sanitized_name'],
                "file_name": unique_filename,
                "file_type": content_type,
                "file_size": upload_result['bytes'],
                "cloudinary_url": upload_result['cloudinary_url'],
                "cloudinary_public_id": upload_result['cloudinary_public_id'],
                "cloudinary_asset_id": upload_result.get("asset_id"),
                "cloudinary_resource_type": upload_result.get("resource_type", "raw"),
                "cloudinary_version": upload_result.get("version"),
                "cloudinary_format": upload_result.get("format"),
                "storage_provider": upload_result.get("storage_provider", "cloudinary"),
                "version": 1,
                "slot": slot,
                "is_primary": (slot == "primary"),
                "is_current": (slot == "primary"),
                "status": "uploaded",
                "analysis_status": "pending",
                "analysis_progress": 0,
                "analysis_stage": "Queued for processing",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            result = self.db[C.RESUMES].insert_one(resume_doc)
            resume_doc["_id"] = result.inserted_id
            resume_doc["id"] = str(result.inserted_id)
            
            # Process text and extract structure synchronously for immediate readiness
            await self._analyze_resume_async(str(result.inserted_id), file_content, content_type)
            
            # Fetch updated resume with parsed_data and analysis
            updated_doc = self.db[C.RESUMES].find_one({"_id": result.inserted_id})
            if updated_doc:
                updated_doc["id"] = str(updated_doc["_id"])
                updated_doc["student_id"] = str(updated_doc["student_id"])
                # Attach latest analysis
                analysis = self.db[C.RESUME_ANALYSES].find_one({"resume_id": result.inserted_id})
                if analysis:
                    updated_doc["score"] = analysis.get("overall_score")
                    updated_doc["ats_score"] = analysis.get("ats_score")
                    updated_doc["analysis"] = analysis
                return updated_doc
            
            resume_doc["student_id"] = str(resume_doc["student_id"])
            return resume_doc
            
        except Exception as e:
            if 'upload_result' in locals() and upload_result.get('cloudinary_public_id'):
                self.cloudinary.delete_file(upload_result['cloudinary_public_id'])
            raise StorageError(f"Resume upload failed: {str(e)}")
    
    async def get_student_resumes(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all resumes for a student with analysis scores."""
        cursor = self.db[C.RESUMES].find(
            {"student_id": ObjectId(student_id)}
        ).sort("created_at", -1)
        
        resumes = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            # Older records may not have timestamps; use the Mongo ID creation time
            # instead of displaying an invalid date in the student vault.
            doc.setdefault("created_at", doc["_id"].generation_time)
            doc.setdefault("updated_at", doc.get("created_at"))
            doc.setdefault("original_file_name", doc.get("name") or doc.get("file_name"))
            doc["student_id"] = str(doc.get("student_id", student_id))
            doc["slot"] = doc.get("slot") or ("primary" if doc.get("is_primary") else "secondary")
            doc["is_primary"] = (doc["slot"] == "primary")
            
            # Attach analysis score if present
            analysis = self.db[C.RESUME_ANALYSES].find_one(
                {"resume_id": doc["_id"]},
                sort=[("created_at", -1)]
            )
            if analysis:
                doc["score"] = analysis.get("overall_score")
                doc["ats_score"] = analysis.get("ats_score")
                doc["analysis"] = analysis
            else:
                doc["score"] = doc.get("score")
                doc["ats_score"] = doc.get("ats_score")
            
            resumes.append(doc)
        
        return resumes
    
    async def set_resume_slot(self, resume_id: str, student_id: str, slot: str) -> Dict[str, Any]:
        """Set resume slot to 'primary' or 'secondary'."""
        if slot not in ("primary", "secondary"):
            raise ValidationError("Slot must be 'primary' or 'secondary'")
        
        owner_id = ObjectId(student_id)
        target_id = ObjectId(resume_id)
        target = self.db[C.RESUMES].find_one({"_id": target_id, "student_id": owner_id})
        if not target:
            raise NotFoundError("Resume")

        prior_slot = target.get("slot") or ("primary" if target.get("is_primary") else "secondary")
        occupant = self.db[C.RESUMES].find_one({
            "student_id": owner_id,
            "slot": slot,
            "_id": {"$ne": target_id},
        })
        if occupant and prior_slot in ("primary", "secondary"):
            self.db[C.RESUMES].update_one(
                {"_id": occupant["_id"]},
                {"$set": {
                    "slot": prior_slot,
                    "is_primary": prior_slot == "primary",
                    "is_current": prior_slot == "primary",
                    "updated_at": utc_now(),
                }}
            )
        self.db[C.RESUMES].update_one(
            {"_id": target_id, "student_id": owner_id},
            {"$set": {
                "slot": slot,
                "is_primary": slot == "primary",
                "is_current": slot == "primary",
                "updated_at": utc_now(),
            }}
        )
        return await self.get_resume_by_id(resume_id, student_id)
    
    async def get_resume_by_id(self, resume_id: str, student_id: str = None) -> Dict[str, Any]:
        """Get resume by ID."""
        filter_dict = {"_id": ObjectId(resume_id)}
        if student_id:
            filter_dict["student_id"] = ObjectId(student_id)
        
        resume = self.db[C.RESUMES].find_one(filter_dict)
        if not resume:
            raise NotFoundError("Resume")
        
        resume["id"] = str(resume["_id"])
        resume["slot"] = resume.get("slot") or ("primary" if resume.get("is_primary") else "secondary")
        resume["is_primary"] = (resume["slot"] == "primary")
        
        analysis = self.db[C.RESUME_ANALYSES].find_one({"resume_id": resume["_id"]})
        if analysis:
            resume["score"] = analysis.get("overall_score")
            resume["ats_score"] = analysis.get("ats_score")
            resume["analysis"] = analysis
            
        return resume
    
    async def delete_resume(self, resume_id: str, student_id: str) -> None:
        """Delete resume and associated data."""
        resume = await self.get_resume_by_id(resume_id, student_id)
        
        # Delete from Cloudinary Storage
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
            {"resume_id": ObjectId(resume_id), "generated_by": "gemini"}
        ).sort("created_at", -1)
        
        improvements = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc["resume_id"] = str(doc["resume_id"])
            doc["student_id"] = str(doc["student_id"])
            improvements.append(doc)
        
        return improvements

    async def generate_resume_improvements(self, resume_id: str, student_id: str, target_role: str) -> List[Dict[str, Any]]:
        """Generate role-specific rewrites grounded only in this user's parsed resume."""
        resume = await self.get_resume_by_id(resume_id, student_id)
        parsed = resume.get("parsed_data") or {}
        source_bullets = []

        for item in parsed.get("experience") or []:
            label = " / ".join(part for part in [item.get("position"), item.get("company")] if part) or "Experience"
            for bullet in item.get("key_points") or []:
                if isinstance(bullet, str) and bullet.strip():
                    source_bullets.append({"section": label, "original_text": bullet.strip()})
        for item in parsed.get("projects") or []:
            label = item.get("project_name") or item.get("projectName") or "Project"
            for bullet in item.get("key_points") or []:
                if isinstance(bullet, str) and bullet.strip():
                    source_bullets.append({"section": label, "original_text": bullet.strip()})

        if not source_bullets:
            raise ValidationError("No experience or project bullet points were parsed from this resume to rewrite.")

        from app.ml.gemini_service import gemini_interview_service
        if not gemini_interview_service.api_key:
            raise ProcessingError("Resume enhancement requires GEMINI_API_KEY in backend/.env.")

        import asyncio
        suggestions = await asyncio.to_thread(
            gemini_interview_service.generate_resume_enhancements,
            target_role.strip(),
            source_bullets,
        )
        if not suggestions:
            raise ProcessingError("Gemini could not generate valid resume edits. Check the API key and try again.")

        docs = [{
            "resume_id": ObjectId(resume_id),
            "student_id": ObjectId(student_id),
            "section": suggestion["section"],
            "original_text": suggestion["original_text"],
            "suggested_text": suggestion["suggested_text"],
            "reason": suggestion["reason"],
            "improvement_type": "role_targeted",
            "target_role": target_role.strip(),
            "generated_by": "gemini",
            "status": "pending",
            "created_at": utc_now(),
        } for suggestion in suggestions]
        result = self.db[C.RESUME_IMPROVEMENTS].insert_many(docs)
        for doc, object_id in zip(docs, result.inserted_ids):
            doc["id"] = str(object_id)
            doc["resume_id"] = resume_id
            doc["student_id"] = student_id
        return docs
    
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
        
        improvement["status"] = status
        improvement["id"] = str(improvement["_id"])
        improvement["resume_id"] = str(improvement["resume_id"])
        improvement["student_id"] = str(improvement["student_id"])
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

            # Store structured NLP results alongside the extracted resume fields.
            # SentenceTransformer embeddings are JSON-safe and reusable for matching.
            from app.ml.nlp_processor import nlp_processor
            from app.ml.embeddings import embedding_service

            nlp_processor.load()
            entities = nlp_processor.extract_entities(raw_text) or {}
            extracted_skills = sorted(nlp_processor.extract_skills(raw_text))
            embedding_service.load_model()
            embedding = embedding_service.encode_text(raw_text[:12000]).tolist()
            parsed_data["nlp"] = {
                "entities": entities,
                "normalized_skills": extracted_skills,
                "skill_extraction": "spaCy skill dictionary with normalization" if nlp_processor.is_loaded else "regex skill fallback; spaCy model unavailable",
                "spacy_model": "en_core_web_sm" if nlp_processor.is_loaded else None,
                "semantic_embedding": {
                    "model": embedding_service.model_name,
                    "engine": embedding_service.engine_name,
                    "dimension": len(embedding),
                    "vector": embedding,
                },
            }
            
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
                "ats_checks": ats_checks,
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
