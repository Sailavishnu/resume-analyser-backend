from fastapi import APIRouter

router = APIRouter(prefix="/resumes", tags=["Resumes & PDF Parsing"])

@router.get("/status")
def resumes_status():
    return {"status": "resume parser service ready"}
