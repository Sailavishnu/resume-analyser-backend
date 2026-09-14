"""
Job management service for HR users.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List, Optional

from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.utils.dates import utc_now
from app.utils.pagination import paginate_query, PaginationMeta
from app.db import collections as C


class JobService:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_job(self, job_data: dict, hr_user_id: str) -> Dict[str, Any]:
        """Create a new job posting."""
        # Get HR profile to verify company
        hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
        if not hr_profile:
            raise NotFoundError("HR profile not found")
        
        company_id = hr_profile.get("company_id")
        if not company_id:
            raise ValidationError("HR user must be associated with a company")
        
        # Validate matching config if provided
        if "matching_config" in job_data and job_data["matching_config"]:
            config = job_data["matching_config"]
            total = config.get("skills", 0) + config.get("experience", 0) + config.get("education", 0) + config.get("projects", 0)
            if total != 100:
                raise ValidationError("Matching config weights must sum to 100")
        
        # Create job document
        job_doc = {
            "company_id": company_id,
            "created_by": ObjectId(hr_user_id),
            "title": job_data["title"],
            "description": job_data["description"],
            "location": job_data["location"],
            "work_mode": job_data.get("work_mode", "On-site"),
            "experience_min": job_data.get("experience_min", 0),
            "experience_max": job_data.get("experience_max", 2),
            "salary_min": job_data.get("salary_min"),
            "salary_max": job_data.get("salary_max"),
            "status": "draft",
            "required_skills": job_data.get("required_skills", []),
            "preferred_skills": job_data.get("preferred_skills", []),
            "matching_config": job_data.get("matching_config", {
                "skills": 40, "experience": 30, "education": 15, "projects": 15
            }),
            "applicant_count": 0,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "expires_at": job_data.get("expires_at"),
        }
        
        result = self.db[C.JOBS].insert_one(job_doc)
        job_doc["_id"] = result.inserted_id
        job_doc["id"] = str(result.inserted_id)
        
        return job_doc
    
    async def get_job_by_id(self, job_id: str, include_company: bool = True) -> Dict[str, Any]:
        """Get job by ID with optional company details."""
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        
        job["id"] = str(job["_id"])
        
        # Include company information
        if include_company and job.get("company_id"):
            company = self.db[C.COMPANIES].find_one({"_id": job["company_id"]})
            if company:
                job["company_name"] = company.get("name")
                job["company_logo"] = company.get("logo_url")
        
        return job
    
    async def update_job(self, job_id: str, updates: dict, hr_user_id: str) -> Dict[str, Any]:
        """Update job (only by creator or company HR)."""
        job = await self.get_job_by_id(job_id, include_company=False)
        
        # Verify permission
        if str(job["created_by"]) != hr_user_id:
            # Check if same company
            hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
            if not hr_profile or hr_profile.get("company_id") != job["company_id"]:
                raise ForbiddenError("Not authorized to edit this job")
        
        # Validate matching config if being updated
        if "matching_config" in updates and updates["matching_config"]:
            config = updates["matching_config"]
            total = config.get("skills", 0) + config.get("experience", 0) + config.get("education", 0) + config.get("projects", 0)
            if total != 100:
                raise ValidationError("Matching config weights must sum to 100")
        
        # Update job
        updates["updated_at"] = utc_now()
        self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": updates}
        )
        
        return await self.get_job_by_id(job_id)
    
    async def delete_job(self, job_id: str, hr_user_id: str) -> None:
        """Delete job (only by creator)."""
        job = await self.get_job_by_id(job_id, include_company=False)
        
        # Verify permission
        if str(job["created_by"]) != hr_user_id:
            raise ForbiddenError("Only job creator can delete the job")
        
        # Check if job has applications
        app_count = self.db[C.APPLICATIONS].count_documents({"job_id": ObjectId(job_id)})
        if app_count > 0:
            raise ValidationError("Cannot delete job with existing applications")
        
        self.db[C.JOBS].delete_one({"_id": ObjectId(job_id)})
    
    async def get_company_jobs(
        self, 
        hr_user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], PaginationMeta]:
        """Get jobs for HR user's company."""
        # Get HR company
        hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
        if not hr_profile or not hr_profile.get("company_id"):
            return [], PaginationMeta(page=page, page_size=page_size, total=0, total_pages=0)
        
        # Build filter
        filter_dict = {"company_id": hr_profile["company_id"]}
        if status_filter:
            filter_dict["status"] = status_filter
        
        # Get paginated results
        jobs, pagination = paginate_query(
            self.db[C.JOBS],
            filter_dict,
            page=page,
            page_size=page_size,
            sort_field="created_at",
            sort_direction=-1
        )
        
        # Add IDs and company info
        for job in jobs:
            job["id"] = str(job["_id"])
        
        return jobs, pagination
    
    async def get_public_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None
    ) -> tuple[List[Dict[str, Any]], PaginationMeta]:
        """Get active jobs for student browsing."""
        # Build filter for active jobs only
        filter_dict = {"status": "active"}
        
        if filters:
            if filters.get("location"):
                filter_dict["location"] = {"$regex": filters["location"], "$options": "i"}
            if filters.get("work_mode"):
                filter_dict["work_mode"] = filters["work_mode"]
            if filters.get("required_skills"):
                filter_dict["required_skills"] = {"$in": filters["required_skills"]}
            if filters.get("experience_max"):
                filter_dict["experience_min"] = {"$lte": filters["experience_max"]}
        
        # Get paginated results
        jobs, pagination = paginate_query(
            self.db[C.JOBS],
            filter_dict,
            page=page,
            page_size=page_size,
            sort_field="created_at",
            sort_direction=-1
        )
        
        # Enrich with company data
        company_ids = [job.get("company_id") for job in jobs if job.get("company_id")]
        companies = {
            company["_id"]: company 
            for company in self.db[C.COMPANIES].find({"_id": {"$in": company_ids}})
        }
        
        for job in jobs:
            job["id"] = str(job["_id"])
            company = companies.get(job.get("company_id"))
            if company:
                job["company_name"] = company.get("name")
                job["company_logo"] = company.get("logo_url")
        
        return jobs, pagination
    
    async def increment_applicant_count(self, job_id: str) -> None:
        """Increment applicant count when someone applies."""
        self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$inc": {"applicant_count": 1}}
        )
    
    async def publish_job(self, job_id: str, hr_user_id: str) -> Dict[str, Any]:
        """Publish a draft job (make it active)."""
        job = await self.get_job_by_id(job_id, include_company=False)
        
        # Verify permission
        if str(job["created_by"]) != hr_user_id:
            raise ForbiddenError("Only job creator can publish the job")
        
        if job["status"] != "draft":
            raise ValidationError("Only draft jobs can be published")
        
        # Validate required fields
        required_fields = ["title", "description", "location", "required_skills"]
        missing_fields = [field for field in required_fields if not job.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Update status
        self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "active", "updated_at": utc_now()}}
        )
        
        return await self.get_job_by_id(job_id)
    
    async def close_job(self, job_id: str, hr_user_id: str) -> Dict[str, Any]:
        """Close an active job."""
        job = await self.get_job_by_id(job_id, include_company=False)
        
        # Verify permission
        if str(job["created_by"]) != hr_user_id:
            raise ForbiddenError("Only job creator can close the job")
        
        if job["status"] not in ["active", "paused"]:
            raise ValidationError("Only active or paused jobs can be closed")
        
        # Update status
        self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "closed", "updated_at": utc_now()}}
        )
        
        return await self.get_job_by_id(job_id)