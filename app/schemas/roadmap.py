from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoadmapItemRequest(BaseModel):
    title: str
    skill_id: Optional[str] = None
    phase_title: str
    description: Optional[str] = None


class RoadmapItemUpdateRequest(BaseModel):
    status: str  # not_started | in_progress | completed


class RoadmapItem(BaseModel):
    id: str
    title: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    status: str = "not_started"
    completed_at: Optional[datetime] = None


class RoadmapPhase(BaseModel):
    title: str
    order: int
    progress: int = 0
    items: list[RoadmapItem] = []


class RoadmapOut(BaseModel):
    id: str
    student_id: str
    target_role: str
    progress: int = 0
    phases: list[RoadmapPhase] = []
    updated_at: Optional[datetime] = None


class RoadmapCreateRequest(BaseModel):
    target_role: str