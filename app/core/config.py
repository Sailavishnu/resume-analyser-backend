import os
from pathlib import Path
from pydantic import BaseModel

# Load .env file manually (avoid python-dotenv dependency for now)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


class Settings(BaseModel):
    PROJECT_NAME: str = "Resume AI & Placement Platform API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    APP_ENV: str = "development"
    
    # MongoDB
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI",
        "mongodb://localhost:27017"
    )
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "resume_ai_platform")
    
    @property
    def MONGO_URI(self) -> str:
        return self.MONGODB_URI
        
    @property
    def MONGO_DB_NAME(self) -> str:
        return self.MONGODB_DB_NAME
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
        ).split(",")
    ]
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Alias for BACKEND_CORS_ORIGINS"""
        return self.BACKEND_CORS_ORIGINS
    
    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "resume-ai-placement-platform-secret-2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    @property
    def cloudinary_configured(self) -> bool:
        """Check if Cloudinary is configured"""
        return bool(self.CLOUDINARY_CLOUD_NAME and self.CLOUDINARY_API_KEY and self.CLOUDINARY_API_SECRET)
    
    # Admin Credentials
    ADMIN_ID: str = os.getenv("ADMIN_ID", "admin")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@resumeai.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./resume_ai.db")
    
    # ML Model
    ML_MODEL_PATH: str = os.getenv(
        "ML_MODEL_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "ml" / "artifacts" / "resume_job_match_model.joblib")
    )
    
    # Uploads
    UPLOAD_DIR: str = os.getenv(
        "UPLOAD_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    )
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
