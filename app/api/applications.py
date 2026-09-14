"""
Job application management API routes.
"""
from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import List

from app.core.dependencies import get_current_user, require_student, require_hr
from app.db.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse, MessageResponse
from app.schemas.applications import (
    ApplicationCreateRequest, ApplicationUpdateRequest, ApplicationOut,
    ApplicationEventOut, ApplicationNoteRequest, ApplicationNoteOut
)
from app.services.application_service import ApplicationService
from app.utils.pagination import parse_pagination_params

router = APIRouter(prefix="/applications", tags=["Applications"])


# ─── Student application routes ────────────────────────────────────────────

@router.post("", response_model=DataResponse[ApplicationOut])
async def apply_to_job(
    request: ApplicationCreateRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Submit job application."""
    app_service = ApplicationService(db)
    
    application = await app_service.apply_to_job(
        student_id=current_user["id"],
        job_id=request.job_id,
        resume_id=request.resume_id
    )
    
    return DataResponse(data=ApplicationOut(**application))


@router.get("", response_model=PaginatedResponse[ApplicationOut])
async def get_my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get applications for authenticated student."""
    app_service = ApplicationService(db)
    
    applications, pagination = await app_service.get_student_applications(
        student_id=current_user["id"],
        page=page,
        page_size=page_size
    )
    
    return PaginatedResponse(
        data=[ApplicationOut(**app) for app in applications],
        pagination=pagination
    )


@router.get("/{application_id}", response_model=DataResponse[ApplicationOut])
async def get_application(
    application_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Get application details."""
    app_service = ApplicationService(db)
    
    application = await app_service.get_application_by_id(application_id, current_user["id"])
    
    return DataResponse(data=ApplicationOut(**application))


@router.post("/{application_id}/withdraw", response_model=DataResponse[ApplicationOut])
async def withdraw_application(
    application_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Withdraw job application."""
    app_service = ApplicationService(db)
    
    application = await app_service.withdraw_application(application_id, current_user["id"])
    
    return DataResponse(data=ApplicationOut(**application))


@router.get("/{application_id}/timeline", response_model=DataResponse[List[ApplicationEventOut]])
async def get_application_timeline(
    application_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Get application timeline events."""
    app_service = ApplicationService(db)
    
    events = await app_service.get_application_timeline(application_id, current_user["id"])
    
    return DataResponse(data=[ApplicationEventOut(**event) for event in events])


@router.post("/{application_id}/notes", response_model=DataResponse[ApplicationNoteOut])
async def add_application_note(
    application_id: str,
    request: ApplicationNoteRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Add private note to application."""
    app_service = ApplicationService(db)
    
    note = await app_service.add_application_note(
        app_id=application_id,
        student_id=current_user["id"],
        content=request.content
    )
    
    return DataResponse(data=ApplicationNoteOut(**note))


@router.get("/{application_id}/notes", response_model=DataResponse[List[ApplicationNoteOut]])
async def get_application_notes(
    application_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get private notes for application."""
    app_service = ApplicationService(db)
    
    notes = await app_service.get_application_notes(application_id, current_user["id"])
    
    return DataResponse(data=[ApplicationNoteOut(**note) for note in notes])


# ─── HR application management routes ──────────────────────────────────────

@router.patch("/hr/{application_id}/status", response_model=DataResponse[ApplicationOut])
async def update_application_status(
    application_id: str,
    request: ApplicationUpdateRequest,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Update application status (HR only)."""
    request.validate_status()  # Validate status value
    
    app_service = ApplicationService(db)
    
    application = await app_service.update_application_status(
        app_id=application_id,
        new_status=request.status,
        hr_user_id=current_user["id"]
    )
    
    return DataResponse(data=ApplicationOut(**application))