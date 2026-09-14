"""
Resume AI & Placement Platform - FastAPI Application

Complete backend with MongoDB, Cloudinary, ML model, and comprehensive API.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from app.core.config import settings
from app.core.exceptions import (
    AppError, 
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.db.mongodb import connect_db, close_db
from app.ml.predictor import predictor

# Import all API routers
from app.api import (
    auth, users, resumes, ats, jd_match, jobs, 
    applications, candidates, notifications, analytics
)

# ─── FastAPI Application Setup ────────────────────────────────────────────

app = FastAPI(
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# ─── Exception Handlers ───────────────────────────────────────────────────

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ─── Startup & Shutdown Events ────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Connect to MongoDB
    try:
        connect_db()
        print("✅ MongoDB connection established")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
    
    # Load ML model
    try:
        predictor.load_model()
        print("✅ ML model loaded successfully")
    except Exception as e:
        print(f"⚠️  ML model loading failed: {e}")
        print("   → Job matching will be unavailable until model is trained")
    
    # Verify Cloudinary config
    if settings.cloudinary_configured:
        print("✅ Cloudinary configuration found")
    else:
        print("⚠️  Cloudinary not configured - file uploads will fail")
    
    print(f"🌍 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📊 Health Check: http://{settings.HOST}:{settings.PORT}/health")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    print("🛑 Shutting down Resume AI Platform...")
    
    # Close database connection
    close_db()
    print("✅ MongoDB connection closed")
    
    print("👋 Shutdown complete")

# ─── API Route Registration ───────────────────────────────────────────────

# Authentication & User Management
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)

# Resume Management & Analysis
app.include_router(resumes.router, prefix=settings.API_V1_STR)
app.include_router(ats.router, prefix=settings.API_V1_STR)

# Job Matching & Applications
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(jd_match.router, prefix=settings.API_V1_STR)
app.include_router(applications.router, prefix=settings.API_V1_STR)

# HR & Candidate Management
app.include_router(candidates.router, prefix=settings.API_V1_STR)

# Notifications & Analytics
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

# ─── Root & Health Endpoints ──────────────────────────────────────────────

@app.get("/")
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


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    health_status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "timestamp": "2024-02-15T10:30:00Z",  # Would use utc_now()
        "components": {}
    }
    
    # Check MongoDB connection
    try:
        from app.db.mongodb import get_db
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
            "version": predictor.metadata.get("version") if predictor.metadata else "unknown",
            "details": "Model loaded and ready"
        }
    else:
        health_status["components"]["ml_model"] = {
            "status": "unavailable",
            "details": "Model not loaded - train model first"
        }
    
    # Check Cloudinary
    if settings.cloudinary_configured:
        health_status["components"]["file_storage"] = {
            "status": "configured",
            "type": "Cloudinary",
            "details": "Credentials available"
        }
    else:
        health_status["components"]["file_storage"] = {
            "status": "unconfigured",
            "type": "Cloudinary", 
            "details": "Upload functionality unavailable"
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


if __name__ == "__main__":
    start_server()
