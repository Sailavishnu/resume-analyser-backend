from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.cloud.mongodb import get_database
from app.core.dependencies import require_student
from app.schemas.career_roadmap import CareerRoadmapRequest, PhaseCompletionRequest
from app.schemas.common import DataResponse
from app.services.career_roadmap_service import CareerRoadmapService


router = APIRouter(prefix="/roadmap", tags=["Career Roadmap"])


@router.get("", response_model=DataResponse[dict | None])
async def get_roadmap(current_user: dict = Depends(require_student), db: Database = Depends(get_database)):
    return DataResponse(data=CareerRoadmapService(db).get(current_user["id"]))


@router.post("/generate", response_model=DataResponse[dict])
async def generate_roadmap(
    payload: CareerRoadmapRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    roadmap = await CareerRoadmapService(db).generate(current_user["id"], payload.model_dump())
    return DataResponse(data=roadmap)


@router.patch("/phases/{phase_id}", response_model=DataResponse[dict])
async def complete_roadmap_phase(
    phase_id: str,
    payload: PhaseCompletionRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    return DataResponse(data=CareerRoadmapService(db).complete_phase(current_user["id"], phase_id))
