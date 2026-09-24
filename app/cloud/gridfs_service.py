"""
GridFS integration for file storage in MongoDB.
"""
import gridfs
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any

from app.core.exceptions import StorageError


class GridFSService:
    def __init__(self, db: Database):
        self.db = db
        # Initialize GridFS bucket
        self.fs = gridfs.GridFS(db)
    
    def upload_resume(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str,
        student_id: str
    ) -> Dict[str, Any]:
        """
        Upload resume file to MongoDB GridFS.
        
        Returns:
            {
                'file_id': str,
                'bytes': int
            }
        """
        try:
            # Upload file to GridFS
            file_id = self.fs.put(
                file_content,
                filename=filename,
                content_type=content_type,
                metadata={"student_id": student_id}
            )
            
            return {
                'file_id': str(file_id),
                'bytes': len(file_content)
            }
            
        except Exception as e:
            raise StorageError(f"GridFS upload failed: {str(e)}")
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from GridFS.
        Returns True if successful.
        """
        try:
            self.fs.delete(ObjectId(file_id))
            return True
        except Exception:
            return False
            
    def get_file(self, file_id: str):
        """
        Get file from GridFS for streaming.
        Returns GridOut object or None.
        """
        try:
            return self.fs.get(ObjectId(file_id))
        except gridfs.errors.NoFile:
            return None
