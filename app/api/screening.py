"""Temporary HR resume screening with Sentence-BERT and in-memory FAISS."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import secrets
import re
import threading
from zipfile import BadZipFile, ZipFile

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.core.dependencies import require_hr
from app.ml.document_service import DocumentService
from app.ml.embeddings import embedding_service, SENTENCE_TRANSFORMERS_AVAILABLE
from app.ml.nlp_processor import nlp_processor
from app.schemas.common import DataResponse

router = APIRouter(prefix="/hr/screening", tags=["HR - Screening"])
document_service = DocumentService()
MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_TOTAL_UNPACKED = 100 * 1024 * 1024
MAX_RESUMES = 100
MAX_SESSIONS_PER_HR = 3
MAX_TOTAL_SESSIONS = 20
SESSION_TTL = timedelta(minutes=30)
_sessions: dict[str, dict] = {}
_sessions_lock = threading.RLock()


class RankRequest(BaseModel):
    role: str = Field(min_length=2, max_length=160)
    role_details: str = Field(default="", max_length=6000)
    top_k: int = Field(default=100, ge=1, le=100)
    required_skills: list[str] = Field(default_factory=list, max_length=50)


def _cleanup_sessions(now: datetime) -> None:
    expired = [key for key, value in _sessions.items() if value["expires_at"] <= now]
    for key in expired:
        _sessions.pop(key, None)


def _encode_bert(texts: str | list[str]) -> np.ndarray:
    """Use SentenceTransformer directly so the general-purpose hash fallback is never used."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Sentence-BERT is unavailable. Install the backend ML requirements and retry.")
    embedding_service.load_model()
    model = embedding_service._model
    if model is None:
        raise HTTPException(status_code=503, detail="Sentence-BERT model weights could not be loaded.")
    try:
        return np.asarray(model.encode(texts, normalize_embeddings=True, convert_to_numpy=True), dtype=np.float32)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Sentence-BERT could not encode this screening input.") from exc


def _parse_archive(content: bytes) -> tuple[list[dict], object, dict]:
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Sentence-BERT is unavailable. Install the backend ML requirements and retry.")
    try:
        embedding_service.load_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not load Sentence-BERT for resume screening.") from exc
    if embedding_service.engine_name != "sentence-transformers":
        raise HTTPException(status_code=503, detail="Sentence-BERT could not load its model weights; screening was not run with a fallback model.")

    try:
        archive = ZipFile(BytesIO(content))
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Upload a valid ZIP archive.") from exc
    if len(entries) > MAX_RESUMES:
        raise HTTPException(status_code=400, detail=f"ZIP can contain up to {MAX_RESUMES} files.")
    if sum(entry.file_size for entry in entries) > MAX_TOTAL_UNPACKED:
        raise HTTPException(status_code=413, detail="Uncompressed ZIP contents exceed the 100 MB limit.")

    parsed_records = []
    supported_files = 0
    for entry in entries:
        filename = entry.filename.replace("\\", "/").split("/")[-1]
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if extension not in {"pdf", "docx"}:
            continue
        supported_files += 1
        try:
            text = document_service.extract_text_from_bytes(archive.read(entry), extension)
            text = nlp_processor.clean_text(text)
            if len(text) < 40:
                continue
            parsed = document_service.parse_resume_structure(text)
            skills = set(nlp_processor.extract_skills(text))
            skills.update(nlp_processor.normalize_skills([
                skill for values in (parsed.get("skills") or {}).values() for skill in values
            ]))
            parsed_records.append({
                "filename": filename,
                "file_type": extension,
                "full_name": parsed.get("full_name"),
                "email": parsed.get("email"),
                "skills": sorted(skills),
                "experience_years": nlp_processor.extract_experience_years(text),
                "education": parsed.get("education", []),
                "summary": parsed.get("summary"),
                "parsed_text": text[:20000],
            })
        except Exception:
            # Ignore an unreadable item and continue the rest of the ZIP.
            continue
    if not parsed_records:
        raise HTTPException(status_code=422, detail="No readable PDF or DOCX resumes were found in the ZIP.")

    try:
        vectors = _encode_bert([record["parsed_text"] for record in parsed_records])
        vectors = np.ascontiguousarray(vectors.astype(np.float32))
        import faiss
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="FAISS is not installed in the backend environment.") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not build the temporary resume vector index.") from exc
    experience_values = [row["experience_years"] for row in parsed_records if row["experience_years"] is not None]
    statistics = {
        "files_in_zip": len(entries),
        "supported_files": supported_files,
        "parsed_resumes": len(parsed_records),
        "skipped_files": len(entries) - len(parsed_records),
        "pdf_resumes": sum(row["file_type"] == "pdf" for row in parsed_records),
        "docx_resumes": sum(row["file_type"] == "docx" for row in parsed_records),
        "unique_skills": len({skill for row in parsed_records for skill in row["skills"]}),
        "average_experience_years": round(sum(experience_values) / len(experience_values), 1) if experience_values else None,
    }
    return parsed_records, index, statistics


@router.post("/zip", response_model=DataResponse[dict])
async def import_resume_zip(
    archive: UploadFile = File(...),
    current_user: dict = Depends(require_hr),
):
    """Parse a ZIP and index resumes in process memory; nothing is written to MongoDB or disk."""
    content = await archive.read(MAX_ZIP_BYTES + 1)
    if len(content) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail="ZIP archive exceeds the 25 MB limit.")
    records, index, statistics = await run_in_threadpool(_parse_archive, content)
    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(24)
    summaries = [{"filename": row["filename"], "full_name": row["full_name"], "skills": row["skills"], "file_type": row["file_type"]} for row in records]
    with _sessions_lock:
        _cleanup_sessions(now)
        owner_sessions = sorted(
            ((key, value) for key, value in _sessions.items() if value["owner"] == current_user["id"]),
            key=lambda item: item[1]["created_at"],
        )
        while len(owner_sessions) >= MAX_SESSIONS_PER_HR:
            oldest_key, _ = owner_sessions.pop(0)
            _sessions.pop(oldest_key, None)
        while len(_sessions) >= MAX_TOTAL_SESSIONS:
            oldest_key = min(_sessions, key=lambda key: _sessions[key]["created_at"])
            _sessions.pop(oldest_key, None)
        _sessions[session_id] = {
            "owner": current_user["id"], "records": records, "index": index,
            "created_at": now, "expires_at": now + SESSION_TTL,
        }
    return DataResponse(data={
        "session_id": session_id,
        "resume_count": len(records),
        "statistics": statistics,
        "resumes": summaries,
        "expires_in_minutes": 30,
    })


@router.post("/rank/{session_id}", response_model=DataResponse[dict])
async def rank_resume_batch(
    session_id: str,
    request: RankRequest,
    current_user: dict = Depends(require_hr),
):
    """Rank the in-memory FAISS batch against recruiter-provided role details."""
    now = datetime.now(timezone.utc)
    with _sessions_lock:
        _cleanup_sessions(now)
        session = _sessions.get(session_id)
    if not session or session["owner"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Screening batch expired or not found. Import the ZIP again.")
    query_text = " ".join(part.strip() for part in (request.role, request.role_details, " ".join(request.required_skills)) if part and part.strip())
    try:
        query = np.ascontiguousarray(_encode_bert(query_text).reshape(1, -1))
        scores, indices = session["index"].search(query, len(session["records"]))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not rank this resume batch. Retry the screening.") from exc

    required = list(dict.fromkeys(skill.strip() for skill in request.required_skills if skill.strip()))
    normalized_required = [(skill, nlp_processor.normalize_skill(skill)) for skill in required]
    ranked = []
    for similarity, index in zip(scores[0], indices[0]):
        if index < 0:
            continue
        record = session["records"][int(index)]
        parsed_text = record["parsed_text"].casefold()
        matched = [original for original, normalized in normalized_required
                   if normalized in record["skills"] or re.search(r"(?<!\w)" + re.escape(original.casefold()) + r"(?!\w)", parsed_text)]
        coverage = len(matched) / len(required) if required else 0.0
        semantic_score = max(0.0, min(100.0, float(similarity) * 100))
        final_score = round(semantic_score if not required else semantic_score * 0.75 + coverage * 25, 1)
        ranked.append({
            "filename": record["filename"], "full_name": record["full_name"], "email": record["email"],
            "skills": record["skills"], "experience_years": record["experience_years"],
            "education": record["education"], "summary": record["summary"],
            "score": final_score, "semantic_score": round(semantic_score, 1),
            "matched_required_skills": matched,
            "missing_required_skills": [original for original in required if original not in matched],
        })
    ranked.sort(key=lambda row: (row["score"], row["semantic_score"]), reverse=True)
    ranked = ranked[:request.top_k]
    return DataResponse(data={"role": request.role.strip(), "total_ranked": len(ranked), "results": ranked})
