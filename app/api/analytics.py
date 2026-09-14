"""
Analytics API routes.
"""
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.dependencies import require_student, require_hr, require_admin
from app.db.mongodb import get_database
from app.schemas.common import DataResponse
from app.schemas.analytics import StudentAnalyticsOut, HRAnalyticsOut, AdminAnalyticsOut, MLAnalyticsOut
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/student", response_model=DataResponse[StudentAnalyticsOut])
async def get_student_analytics(
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get comprehensive analytics for authenticated student."""
    analytics_service = AnalyticsService(db)
    
    analytics = await analytics_service.get_student_analytics(current_user["id"])
    
    return DataResponse(data=StudentAnalyticsOut(**analytics))


@router.get("/hr/overview", response_model=DataResponse[HRAnalyticsOut])
async def get_hr_analytics(
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get analytics for HR user and their company."""
    analytics_service = AnalyticsService(db)
    
    analytics = await analytics_service.get_hr_analytics(current_user["id"])
    
    return DataResponse(data=HRAnalyticsOut(**analytics))


@router.get("/admin/overview", response_model=DataResponse[AdminAnalyticsOut])
async def get_admin_analytics(
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Get platform-wide analytics for admin."""
    analytics_service = AnalyticsService(db)
    
    analytics = await analytics_service.get_admin_analytics()
    
    return DataResponse(data=AdminAnalyticsOut(**analytics))


@router.get("/admin/ml", response_model=DataResponse[MLAnalyticsOut])
async def get_ml_analytics(
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Get ML model usage analytics."""
    analytics_service = AnalyticsService(db)
    
    analytics = await analytics_service.get_ml_analytics()
    
    return DataResponse(data=MLAnalyticsOut(**analytics))