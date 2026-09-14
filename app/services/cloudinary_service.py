"""
Cloudinary integration for file storage.
"""
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from typing import BinaryIO, Dict, Any

from app.core.config import settings
from app.core.exceptions import StorageError


class CloudinaryService:
    def __init__(self):
        if settings.cloudinary_configured:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
    
    def upload_resume(
        self, 
        file_content: bytes, 
        filename: str, 
        student_id: str
    ) -> Dict[str, Any]:
        """
        Upload resume PDF/DOCX to Cloudinary.
        
        Returns:
            {
                'public_id': str,
                'secure_url': str,
                'resource_type': str,
                'format': str,
                'bytes': int
            }
        """
        if not settings.cloudinary_configured:
            raise StorageError("Cloudinary not configured")
        
        try:
            # Generate unique public ID
            public_id = f"resume_ai/resumes/{student_id}/{filename}"
            
            # Upload file
            result = cloudinary.uploader.upload(
                file_content,
                public_id=public_id,
                resource_type="raw",  # For PDFs, DOCX
                overwrite=True,
                invalidate=True,
            )
            
            return {
                'public_id': result['public_id'],
                'secure_url': result['secure_url'],
                'resource_type': result['resource_type'],
                'format': result.get('format', 'unknown'),
                'bytes': result['bytes']
            }
            
        except CloudinaryError as e:
            raise StorageError(f"File upload failed: {str(e)}")
        except Exception as e:
            raise StorageError(f"Unexpected upload error: {str(e)}")
    
    def delete_file(self, public_id: str) -> bool:
        """
        Delete file from Cloudinary.
        Returns True if successful or file didn't exist.
        """
        if not settings.cloudinary_configured:
            return True  # Fail silently if not configured
        
        try:
            result = cloudinary.uploader.destroy(
                public_id, 
                resource_type="raw",
                invalidate=True
            )
            return result.get('result') in ('ok', 'not found')
        except CloudinaryError:
            return False  # Log error but don't fail the operation
        except Exception:
            return False
    
    def generate_download_url(self, public_id: str) -> str:
        """Generate secure download URL for a file."""
        if not settings.cloudinary_configured:
            raise StorageError("Cloudinary not configured")
        
        return cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="raw",
            secure=True,
            sign_url=True
        )[0]
    
    @property
    def is_configured(self) -> bool:
        """Check if Cloudinary is properly configured."""
        return settings.cloudinary_configured