"""
Cloudinary integration for resume file storage.

Uploads original resume PDFs/DOCX to Cloudinary Cloud Storage as raw resources
and returns secure download URLs. Falls back to local disk storage if
Cloudinary credentials are not configured.
"""
import os
from typing import Dict, Any, Optional
from app.core.config import settings


class CloudinaryService:
    def __init__(self):
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
        self.api_key = settings.CLOUDINARY_API_KEY
        self.api_secret = settings.CLOUDINARY_API_SECRET
        self._initialized = False
        self._init_cloudinary()

    def _init_cloudinary(self):
        if self.cloud_name and self.api_key and self.api_secret:
            try:
                import cloudinary
                cloudinary.config(
                    cloud_name=self.cloud_name,
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    secure=True
                )
                self._initialized = True
            except Exception as e:
                print(f"[CloudinaryService] Initialization warning: {e}")
                self._initialized = False

    def upload_resume(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        student_id: str
    ) -> Dict[str, Any]:
        """
        Upload resume PDF/DOCX to Cloudinary as a raw resource.
        
        Saved under: resumes/{student_id}/
        
        Returns dict with:
            cloudinary_url       – secure download/access URL
            cloudinary_public_id – public ID for resource management / deletion
            bytes                – file size
            filename             – original/sanitized file name
        """
        if self._initialized:
            try:
                import cloudinary.uploader
                
                # Cloudinary raw upload under resumes/{student_id}/
                folder = f"resumes/{student_id}"
                
                upload_result = cloudinary.uploader.upload(
                    file_content,
                    folder=folder,
                    public_id=filename,
                    resource_type="raw",
                    type="upload",
                    access_mode="public",
                    use_filename=True,
                    unique_filename=False,
                    overwrite=True
                )
                
                secure_url = upload_result.get("secure_url") or upload_result.get("url")
                public_id = upload_result.get("public_id")
                
                return {
                    "cloudinary_url": secure_url,
                    "cloudinary_public_id": public_id,
                    "bytes": len(file_content),
                    "filename": filename
                }
            except Exception as e:
                print(f"[CloudinaryService] Upload failed, using local fallback: {e}")

        # Local disk fallback if Cloudinary is not configured or fails
        return self._local_fallback_upload(file_content, filename, student_id)

    def delete_file(self, public_id: str) -> bool:
        """Delete file from Cloudinary by public_id."""
        if not public_id:
            return False
            
        if public_id.startswith("local/"):
            # Local fallback deletion
            local_filename = public_id.replace("local/", "")
            local_path = os.path.join(settings.UPLOAD_DIR, local_filename)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    return True
                except Exception:
                    return False
            return False

        if self._initialized:
            try:
                import cloudinary.uploader
                res = cloudinary.uploader.destroy(public_id, resource_type="raw")
                return res.get("result") in ["ok", "not_found"]
            except Exception as e:
                print(f"[CloudinaryService] Delete failed for {public_id}: {e}")
                return False

        return False

    def _local_fallback_upload(self, file_content: bytes, filename: str, student_id: str) -> Dict[str, Any]:
        """Save file locally if Cloudinary is unavailable."""
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        local_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(file_content)

        local_url = f"http://{settings.HOST}:{settings.PORT}/uploads/{filename}"
        return {
            "cloudinary_url": local_url,
            "cloudinary_public_id": f"local/{filename}",
            "bytes": len(file_content),
            "filename": filename
        }
