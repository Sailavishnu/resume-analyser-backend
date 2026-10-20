"""Ephemeral ZIP resume screening. Resume bytes, parsed text and FAISS index stay in memory."""
from io import BytesIO
from zipfile import ZipFile, BadZipFile

import numpy as np
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pymongo.database import Database

from app.cloud import collections as C
from app.cloud.mongodb import get_database
from app.core.dependencies import require_hr
from app.ml.document_service import DocumentService
from app.ml.embeddings import embedding_service
from app.schemas.common import DataResponse

router = APIRouter(prefix="/hr/screening", tags=["HR - Screening"])
document_service = DocumentService()
MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_TOTAL_UNPACKED = 100 * 1024 * 1024
MAX_RESUMES = 100


@router.post("/zip", response_model=DataResponse[list])
async def screen_resume_zip(
    job_id: str = Form(...),
    archive: UploadFile = File(...),
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database),
):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Select a valid job posting.")
    job = db[C.JOBS].find_one({"_id": ObjectId(job_id), "created_by": ObjectId(current_user["id"])})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found for this HR account.")
    content = await archive.read(MAX_ZIP_BYTES + 1)
    if len(content) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail="ZIP archive exceeds the 25 MB limit.")
    try:
        zip_file = ZipFile(BytesIO(content))
        entries = [entry for entry in zip_file.infolist() if not entry.is_dir()]
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Upload a valid ZIP archive.") from exc
    if len(entries) > MAX_RESUMES:
        raise HTTPException(status_code=400, detail=f"ZIP can contain up to {MAX_RESUMES} files.")
    if sum(item.file_size for item in entries) > MAX_TOTAL_UNPACKED:
        raise HTTPException(status_code=413, detail="Uncompressed ZIP contents exceed the 100 MB limit.")

    candidates = []
    for entry in entries:
        filename = entry.filename.replace("\\", "/").split("/")[-1]
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if extension not in {"pdf", "docx"}:
            continue
        try:
            raw = zip_file.read(entry)
            text = document_service.extract_text_from_bytes(raw, extension)
            if not text.strip():
                continue
            parsed = document_service.parse_resume_structure(text)
            vector = embedding_service.encode_text(text[:20000], normalize=True)
            candidates.append({
                "filename": filename,
                "full_name": parsed.get("full_name"), "email": parsed.get("email"),
                "skills": [skill for group in (parsed.get("skills") or {}).values() for skill in group],
                "experience": parsed.get("experience", []),
                "education": parsed.get("education", []),
                "vector": vector,
            })
        except Exception:
            # One malformed resume should not fail the rest of the batch.
            continue
    if not candidates:
        raise HTTPException(status_code=422, detail="No readable PDF or DOCX resumes were found in the ZIP.")

    try:
        import faiss
        matrix = np.ascontiguousarray(np.stack([item.pop("vector") for item in candidates]).astype("float32"))
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        job_text = " ".join([str(job.get("title", "")), str(job.get("description", "")),
                             " ".join(job.get("required_skills", [])), " ".join(job.get("preferred_skills", []))])
        query = np.ascontiguousarray(embedding_service.encode_text(job_text, normalize=True).reshape(1, -1).astype("float32"))
        scores, indices = index.search(query, len(candidates))
        ordered = [candidates[int(i)] | {"score": round(max(0.0, min(100.0, (float(score) + 1) * 50)), 1)} for score, i in zip(scores[0], indices[0])]
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="FAISS is not installed in the backend environment.") from exc

    for item in ordered:
        actual = {skill.casefold() for skill in item["skills"]}
        item["matched_required_skills"] = [skill for skill in job.get("required_skills", []) if skill.casefold() in actual]
        item.pop("experience", None)
        item.pop("education", None)
    return DataResponse(data=ordered)
