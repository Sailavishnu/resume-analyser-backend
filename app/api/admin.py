"""
Master Admin API Routes.

Provides full administrative control over users, platform content, metrics, system configuration, and PDF report downloads.
Protected by require_admin dependency.
"""
from fastapi import APIRouter, Depends, Query, Body, Response
from pymongo.database import Database
from typing import Optional, Dict, Any

from app.core.dependencies import require_admin
from app.cloud.mongodb import get_database
from app.schemas.common import DataResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Master Admin"])


@router.get("/dashboard", response_model=DataResponse[dict])
async def get_admin_dashboard(
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Get complete master admin dashboard metrics and system health."""
    admin_service = AdminService(db)
    stats = await admin_service.get_dashboard_metrics()
    return DataResponse(data=stats)


@router.get("/reports/pdf")
async def get_admin_pdf_report(
    start_date: str = Query("2026-09-01"),
    end_date: str = Query("2026-09-30"),
    db: Database = Depends(get_database)
):
    """Generate and return native PyMuPDF executive report as direct PDF file download."""
    admin_service = AdminService(db)
    pdf_bytes = await admin_service.generate_pdf_report(start_date, end_date)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Master_Platform_Analysis_{start_date}_to_{end_date}.pdf"
        }
    )


@router.get("/users", response_model=DataResponse[dict])
async def get_users_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """List system users with pagination, role filtering, and search."""
    admin_service = AdminService(db)
    res = await admin_service.get_users_list(
        page=page,
        page_size=page_size,
        role_filter=role,
        search_query=search
    )
    return DataResponse(data=res)


@router.post("/users", response_model=DataResponse[dict])
async def create_user_by_admin(
    payload: dict = Body(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Create a new user account directly via Master Admin."""
    admin_service = AdminService(db)
    res = await admin_service.create_user_by_admin(payload)
    return DataResponse(data=res)


@router.patch("/users/{user_id}/status", response_model=DataResponse[dict])
async def update_user_status(
    user_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Activate or Suspend user account."""
    is_active = payload.get("is_active", True)
    admin_service = AdminService(db)
    res = await admin_service.update_user_status(user_id, is_active)
    return DataResponse(data=res)


@router.patch("/users/{user_id}/role", response_model=DataResponse[dict])
async def update_user_role(
    user_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Change user role (student, hr, admin)."""
    new_role = payload.get("role")
    admin_service = AdminService(db)
    res = await admin_service.update_user_role(user_id, new_role)
    return DataResponse(data=res)


@router.post("/users/{user_id}/reset-password", response_model=DataResponse[dict])
async def reset_user_password(
    user_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Reset user password."""
    new_password = payload.get("password", "Password@123")
    admin_service = AdminService(db)
    res = await admin_service.reset_user_password(user_id, new_password)
    return DataResponse(data=res)


@router.delete("/users/{user_id}", response_model=DataResponse[dict])
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Permanently delete user account and associated data."""
    admin_service = AdminService(db)
    res = await admin_service.delete_user(user_id)
    return DataResponse(data=res)


@router.get("/jobs", response_model=DataResponse[list])
async def get_all_jobs_audit(
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Get all job postings for moderation and audit."""
    admin_service = AdminService(db)
    jobs = await admin_service.get_all_jobs_audit()
    return DataResponse(data=jobs)


@router.patch("/jobs/{job_id}/status", response_model=DataResponse[dict])
async def update_job_status(
    job_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Approve, Flag, or Deactivate job posting."""
    status = payload.get("status", "active")
    admin_service = AdminService(db)
    res = await admin_service.update_job_status(job_id, status)
    return DataResponse(data=res)
