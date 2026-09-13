from fastapi import APIRouter

router = APIRouter(prefix="/jobs", tags=["Jobs & Applications"])

@router.get("/status")
def jobs_status():
    return {"status": "jobs & applications service ready"}
