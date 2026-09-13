from fastapi import APIRouter

router = APIRouter(prefix="/ats", tags=["ATS Scoring & Analysis"])

@router.get("/status")
def ats_status():
    return {"status": "ats scoring engine ready"}
