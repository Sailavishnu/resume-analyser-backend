"""
Analytics service for generating platform metrics and insights.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.utils.dates import utc_now
from app.db import collections as C


class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_student_analytics(self, student_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a student."""
        
        # Get student profile
        profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": ObjectId(student_id)})
        
        # Application breakdown
        applications = list(self.db[C.APPLICATIONS].find({"student_id": ObjectId(student_id)}))
        app_breakdown = {}
        for status in ["applied", "under_review", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"]:
            app_breakdown[status] = sum(1 for app in applications if app.get("status") == status)
        
        # Resume analysis
        latest_resume = self.db[C.RESUMES].find_one(
            {"student_id": ObjectId(student_id), "is_current": True}
        )
        latest_analysis = None
        if latest_resume:
            latest_analysis = self.db[C.RESUME_ANALYSES].find_one(
                {"resume_id": latest_resume["_id"]},
                sort=[("created_at", -1)]
            )
        
        # Career readiness history
        history = list(self.db[C.CAREER_READINESS_HISTORY].find(
            {"student_id": ObjectId(student_id)}
        ).sort("created_at", -1).limit(10))
        
        career_history = [
            {
                "date": h["created_at"].strftime("%Y-%m-%d"),
                "score": h.get("score", 0)
            }
            for h in history
        ]
        
        # Interview and assessment counts
        interview_count = self.db[C.MOCK_INTERVIEWS].count_documents({"student_id": ObjectId(student_id)})
        assessment_count = self.db[C.ASSESSMENT_ATTEMPTS].count_documents({"student_id": ObjectId(student_id)})
        
        return {
            "student_id": student_id,
            "career_readiness_score": profile.get("career_readiness_score", 0) if profile else 0,
            "resume_health_score": latest_analysis.get("overall_score") if latest_analysis else None,
            "ats_score": latest_analysis.get("ats_score") if latest_analysis else None,
            "current_streak": profile.get("current_streak", 0) if profile else 0,
            "longest_streak": profile.get("longest_streak", 0) if profile else 0,
            "total_applications": len(applications),
            "total_interviews": interview_count,
            "total_assessments": assessment_count,
            "roadmap_progress": 0,  # Would calculate from roadmap
            "career_history": career_history,
            "application_breakdown": app_breakdown
        }
    
    async def get_hr_analytics(self, hr_user_id: str) -> Dict[str, Any]:
        """Get analytics for HR user and their company."""
        
        # Get HR profile and company
        hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
        if not hr_profile or not hr_profile.get("company_id"):
            return {"error": "HR profile or company not found"}
        
        company_id = hr_profile["company_id"]
        
        # Job metrics
        jobs = list(self.db[C.JOBS].find({"company_id": company_id}))
        active_jobs = sum(1 for job in jobs if job.get("status") == "active")
        
        # Application metrics
        job_ids = [job["_id"] for job in jobs]
        applications = list(self.db[C.APPLICATIONS].find({"job_id": {"$in": job_ids}}))
        
        total_applicants = len(applications)
        shortlisted = sum(1 for app in applications if app.get("status") == "shortlisted")
        interviewed = sum(1 for app in applications if app.get("status") == "interview")
        hired = sum(1 for app in applications if app.get("status") == "hired")
        
        # Pipeline conversion rates
        pipeline_metrics = {
            "applied_to_shortlisted": (shortlisted / total_applicants * 100) if total_applicants > 0 else 0,
            "shortlisted_to_interviewed": (interviewed / shortlisted * 100) if shortlisted > 0 else 0,
            "interviewed_to_offered": 0,  # Would calculate from offers
            "offered_to_hired": 0
        }
        
        # Job-specific metrics
        job_metrics = []
        for job in jobs:
            job_apps = [app for app in applications if app["job_id"] == job["_id"]]
            job_shortlisted = sum(1 for app in job_apps if app.get("status") == "shortlisted")
            job_interviewed = sum(1 for app in job_apps if app.get("status") == "interview")
            job_hired = sum(1 for app in job_apps if app.get("status") == "hired")
            
            conversion_rate = (job_hired / len(job_apps) * 100) if job_apps else 0
            
            job_metrics.append({
                "job_id": str(job["_id"]),
                "job_title": job.get("title", ""),
                "total_applicants": len(job_apps),
                "shortlisted": job_shortlisted,
                "interviewed": job_interviewed,
                "offered": 0,
                "hired": job_hired,
                "avg_match_score": None,  # Would calculate from matches
                "conversion_rate": conversion_rate
            })
        
        return {
            "recruiter_id": hr_user_id,
            "company_id": str(company_id),
            "active_jobs": active_jobs,
            "total_applicants": total_applicants,
            "total_shortlisted": shortlisted,
            "total_interviewed": interviewed,
            "total_hired": hired,
            "avg_match_score": None,  # Would calculate from job matches
            "pipeline_metrics": pipeline_metrics,
            "job_metrics": job_metrics,
            "top_skills": []  # Would analyze from applications
        }
    
    async def get_admin_analytics(self) -> Dict[str, Any]:
        """Get platform-wide analytics for admin."""
        
        # User counts
        total_users = self.db[C.USERS].count_documents({})
        students = self.db[C.USERS].count_documents({"role": "student"})
        recruiters = self.db[C.USERS].count_documents({"role": "hr"})
        companies = self.db[C.COMPANIES].count_documents({})
        
        # Job and application counts
        total_jobs = self.db[C.JOBS].count_documents({})
        active_jobs = self.db[C.JOBS].count_documents({"status": "active"})
        total_applications = self.db[C.APPLICATIONS].count_documents({})
        total_resumes = self.db[C.RESUMES].count_documents({})
        total_analyses = self.db[C.RESUME_ANALYSES].count_documents({})
        
        # User growth (last 30 days)
        thirty_days_ago = utc_now() - timedelta(days=30)
        user_growth = []
        
        for i in range(7):  # Last 7 periods (4-5 days each)
            period_start = thirty_days_ago + timedelta(days=i*4)
            period_end = period_start + timedelta(days=4)
            
            period_students = self.db[C.USERS].count_documents({
                "role": "student",
                "created_at": {"$gte": period_start, "$lt": period_end}
            })
            period_recruiters = self.db[C.USERS].count_documents({
                "role": "hr", 
                "created_at": {"$gte": period_start, "$lt": period_end}
            })
            
            user_growth.append({
                "date": period_start.strftime("%Y-%m-%d"),
                "students": period_students,
                "recruiters": period_recruiters,
                "total": period_students + period_recruiters
            })
        
        # Feature usage (simplified)
        feature_usage = [
            {"feature": "Resume Analysis", "usage_count": total_analyses},
            {"feature": "Job Applications", "usage_count": total_applications},
            {"feature": "Job Matches", "usage_count": self.db[C.JOB_MATCHES].count_documents({})},
            {"feature": "Mock Interviews", "usage_count": self.db[C.MOCK_INTERVIEWS].count_documents({})}
        ]
        
        return {
            "total_users": total_users,
            "total_students": students,
            "total_recruiters": recruiters,
            "total_companies": companies,
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "total_resumes": total_resumes,
            "total_analyses": total_analyses,
            "active_jobs": active_jobs,
            "user_growth": user_growth,
            "feature_usage": feature_usage
        }
    
    async def get_ml_analytics(self) -> Dict[str, Any]:
        """Get ML model usage analytics."""
        
        # Match prediction counts
        total_predictions = self.db[C.JOB_MATCHES].count_documents({})
        
        # Score distribution
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lt": ["$display_score", 50]}, "then": "0-50"},
                                {"case": {"$lt": ["$display_score", 70]}, "then": "50-70"},
                                {"case": {"$lt": ["$display_score", 85]}, "then": "70-85"},
                                {"case": {"$gte": ["$display_score", 85]}, "then": "85-100"}
                            ],
                            "default": "unknown"
                        }
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        
        distribution_result = list(self.db[C.JOB_MATCHES].aggregate(pipeline))
        prediction_distribution = {item["_id"]: item["count"] for item in distribution_result}
        
        # Feature importance (from latest model metadata - would be loaded from ML service)
        feature_importance = {
            "skill_overlap": 0.25,
            "required_skill_coverage": 0.23,
            "experience_similarity": 0.18,
            "project_relevance": 0.16,
            "keyword_overlap": 0.12,
            "education_match": 0.06
        }
        
        return {
            "model_version": "1.0",
            "total_predictions": total_predictions,
            "avg_confidence": None,  # Would calculate from confidence scores
            "prediction_distribution": prediction_distribution,
            "feature_importance": feature_importance
        }