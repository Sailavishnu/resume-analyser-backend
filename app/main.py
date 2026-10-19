"""
Resume AI & Placement Platform - FastAPI Application

Complete backend with MongoDB, ML model, and comprehensive API.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import sys
import io
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn

from app.core.config import settings
from app.utils.dates import utc_now as health_utc_now
from app.core.exceptions import (
    AppError, 
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.cloud.mongodb import connect_db, close_db
from app.ml.predictor import predictor

# Import all API routers
from app.api import (
    auth, users, admin, resumes, ats, jd_match, jobs,
    applications, candidates, notifications, analytics, interviews, messages, practice
)


# ─── FastAPI Application Setup ────────────────────────────────────────────

api_app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Complete Resume AI & Placement Platform API with ML-powered job matching",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Resume AI Platform",
        "url": "https://github.com/your-org/resume-ai-platform",
    },
    license_info={
        "name": "MIT License",
    },
)

# ─── CORS Middleware ──────────────────────────────────────────────────────

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Exception Handlers ───────────────────────────────────────────────────

api_app.add_exception_handler(AppError, app_error_handler)
api_app.add_exception_handler(StarletteHTTPException, http_exception_handler)
api_app.add_exception_handler(RequestValidationError, validation_exception_handler)
api_app.add_exception_handler(Exception, unhandled_exception_handler)

# ─── Startup & Shutdown Events ────────────────────────────────────────────

@api_app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Connect to MongoDB
    try:
        connect_db()
        from app.cloud.mongodb import get_db
        db = get_db()
        db["conversations"].create_index([("participants", 1), ("updated_at", -1)])
        db["messages"].create_index([("conversation_id", 1), ("created_at", 1)])
        db["notifications"].create_index([("user_id", 1), ("is_read", 1), ("created_at", -1)])
        db["practice_attempts"].create_index([("user_id", 1), ("created_at", -1)])
        db["practice_attempts"].create_index(
            [("user_id", 1), ("submission_id", 1)],
            unique=True,
            partialFilterExpression={"submission_id": {"$type": "string"}},
        )
        print("✅ MongoDB connection established")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
    
    # Verify Cloudinary Storage config
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        print("✅ Cloudinary Storage configuration found")
    else:
        print("⚠️  Cloudinary not configured - file uploads will use local fallback")
    
    # Asynchronous non-blocking model warm-up (fast startup, zero waiting)
    import asyncio
    async def _warmup_ml():
        try:
            from app.ml.predictor import predictor
            predictor.load_model()
            from app.ml.embeddings import embedding_service
            if not embedding_service.is_loaded:
                embedding_service.load_model()
            from app.ml.nlp_processor import nlp_processor
            nlp_processor.load()
            from app.ml.vector_store import get_vector_store
            vector_store = get_vector_store()
            vector_store.load()
            print("⚡ ML custom model, embeddings & vector store ready")
        except Exception as err:
            print(f"⚠️  ML background warm-up notice: {err}")
    
    asyncio.create_task(_warmup_ml())

    print(f"\nAPI Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📊 Health Check: http://{settings.HOST}:{settings.PORT}/health")


@api_app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    print("🛑 Shutting down Resume AI Platform...")
    
    # Close database connection
    close_db()
    print("✅ MongoDB connection closed")
    
    print("👋 Shutdown complete")

# ─── API Route Registration ───────────────────────────────────────────────

# Authentication & User Management
api_app.include_router(auth.router, prefix=settings.API_V1_STR)
api_app.include_router(users.router, prefix=settings.API_V1_STR)

# Resume Management & Analysis
api_app.include_router(resumes.router, prefix=settings.API_V1_STR)
api_app.include_router(ats.router, prefix=settings.API_V1_STR)

# Job Matching & Applications
api_app.include_router(jobs.router, prefix=settings.API_V1_STR)
api_app.include_router(jd_match.router, prefix=settings.API_V1_STR)
api_app.include_router(applications.router, prefix=settings.API_V1_STR)

# Master Admin Console & System Control
api_app.include_router(admin.router, prefix=settings.API_V1_STR)

# HR & Candidate Management
api_app.include_router(candidates.router, prefix=settings.API_V1_STR)

# Notifications & Analytics
api_app.include_router(notifications.router, prefix=settings.API_V1_STR)
api_app.include_router(analytics.router, prefix=settings.API_V1_STR)
api_app.include_router(practice.router, prefix=settings.API_V1_STR)

# AI Mock Interviews
api_app.include_router(interviews.router, prefix=settings.API_V1_STR)

api_app.include_router(messages.router, prefix=settings.API_V1_STR)

# Static files for local uploads fallback
from fastapi.staticfiles import StaticFiles
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
api_app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ─── Root & Health Endpoints ──────────────────────────────────────────────

@api_app.get("/")
async def root():
    """API root endpoint with service information."""
    return {
        "message": "Welcome to Resume AI & Placement Platform API",
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/health",
            "api": settings.API_V1_STR
        },
        "features": [
            "User Authentication & Authorization",
            "Resume Upload & Analysis",
            "ATS Compatibility Scoring", 
            "ML-Powered Job Matching",
            "Job Application Tracking",
            "HR Candidate Management",
            "Real-time Notifications",
            "Comprehensive Analytics"
        ]
    }


@api_app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    health_status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "timestamp": str(health_utc_now()),
        "components": {}
    }
    
    # Check MongoDB connection
    try:
        from app.cloud.mongodb import get_db
        db = get_db()
        db.command("ping")
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "MongoDB",
            "details": "Connection active"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy", 
            "type": "MongoDB",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check ML model
    if predictor.is_loaded:
        health_status["components"]["ml_model"] = {
            "status": "healthy",
            "version": getattr(predictor, "version", "2.0-semantic-rag"),
            "details": "Custom Random Forest + Semantic Match Model ready"
        }
    else:
        health_status["components"]["ml_model"] = {
            "status": "unavailable",
            "details": "Model not loaded"
        }
    
    # Check NLP models
    try:
        from app.ml.nlp_processor import nlp_processor
        if nlp_processor.is_loaded:
            health_status["components"]["nlp_spacy"] = {
                "status": "healthy",
                "model": "en_core_web_sm",
                "details": "spaCy NLP ready"
            }
        else:
            health_status["components"]["nlp_spacy"] = {
                "status": "unavailable",
                "details": "Run: python -m spacy download en_core_web_sm"
            }
    except Exception as e:
        health_status["components"]["nlp_spacy"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Sentence-BERT
    try:
        from app.ml.embeddings import embedding_service
        if embedding_service.is_loaded:
            health_status["components"]["embeddings"] = {
                "status": "healthy",
                "model": "all-MiniLM-L6-v2",
                "dimension": 384,
                "details": "Sentence-BERT ready"
            }
        else:
            health_status["components"]["embeddings"] = {
                "status": "unavailable",
                "details": "Model will auto-download on first use"
            }
    except Exception as e:
        health_status["components"]["embeddings"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check FAISS vector index
    try:
        from app.ml.vector_store import get_vector_store
        vector_store = get_vector_store()
        if vector_store.is_built():
            health_status["components"]["vector_search"] = {
                "status": "healthy",
                "type": "FAISS",
                "jobs_indexed": vector_store.size(),
                "details": "Semantic search ready"
            }
        else:
            health_status["components"]["vector_search"] = {
                "status": "unavailable",
                "details": "Run: python ml/scripts/build_vector_index.py"
            }
    except Exception as e:
        health_status["components"]["vector_search"] = {
            "status": "error",
            "error": str(e)
        }
    
    return health_status


# ─── Development Server Runner ────────────────────────────────────────────

def start_server():
    """Start the development server."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )


import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.cors_origins_list)


@sio.event
async def connect(sid, environ, auth=None):
    from app.core.security import decode_access_token
    from app.cloud.mongodb import get_db
    from bson import ObjectId

    token = (auth or {}).get("token")
    if not token:
        return False
    try:
        user_id = decode_access_token(token).get("sub")
        user = get_db()["users"].find_one({"_id": ObjectId(user_id), "is_active": {"$ne": False}})
        if not user or user.get("role") not in {"student", "hr"}:
            return False
        await sio.save_session(sid, {"user_id": str(user["_id"]), "role": user["role"]})
        await sio.enter_room(sid, f"user:{user['_id']}")
    except Exception:
        return False


@sio.on("message:send")
async def socket_send_message(sid, payload):
    from app.cloud.mongodb import get_db
    from app.api.messages import persist_message
    session = await sio.get_session(sid)
    message, notification = persist_message(get_db(), session["user_id"], payload.get("conversation_id"), payload.get("body"))
    if message:
        conversation = get_db()["conversations"].find_one({"_id": ObjectId(payload.get("conversation_id"))})
        for participant in conversation["participants"]:
            await sio.emit("message:new", message, room=f"user:{participant}")
        if notification:
            await sio.emit("notification:new", notification, room=f"user:{notification['user_id']}")


@sio.event
async def disconnect(sid, reason=None):
    return


from bson import ObjectId
app = socketio.ASGIApp(sio, other_asgi_app=api_app, socketio_path="socket.io")


if __name__ == "__main__":
    start_server()
