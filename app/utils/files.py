"""
File handling utilities: validation, size formatting, extension checking.
"""
import re
from pathlib import Path
from typing import BinaryIO


# ─── File validation ──────────────────────────────────────────────────────────

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_RESUME_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

MAX_FILENAME_LENGTH = 100


def validate_resume_file(filename: str, content_type: str | None, file_size: int, max_size_bytes: int) -> dict:
    """
    Validate an uploaded resume file.
    Returns {"valid": bool, "errors": [str], "sanitized_name": str}.
    """
    errors = []
    
    # Check filename length
    if len(filename) > MAX_FILENAME_LENGTH:
        errors.append(f"Filename too long (max {MAX_FILENAME_LENGTH} characters)")
    
    # Check file extension
    file_path = Path(filename)
    extension = file_path.suffix.lower()
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        errors.append(f"Invalid file type. Allowed: {', '.join(ALLOWED_RESUME_EXTENSIONS)}")
    
    # Check MIME type if provided
    if content_type and content_type not in ALLOWED_RESUME_MIMES:
        errors.append(f"Invalid content type: {content_type}")
    
    # Check file size
    if file_size > max_size_bytes:
        errors.append(f"File too large (max {format_file_size(max_size_bytes)})")
    
    if file_size == 0:
        errors.append("File is empty")
    
    # Sanitize filename
    sanitized = sanitize_filename(filename)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "sanitized_name": sanitized,
        "extension": extension,
    }


def sanitize_filename(filename: str) -> str:
    """
    Remove unsafe characters from filename while preserving extension.
    """
    file_path = Path(filename)
    name_part = file_path.stem
    extension = file_path.suffix
    
    # Remove/replace unsafe characters
    safe_name = re.sub(r'[^\w\-_.]', '_', name_part)
    safe_name = re.sub(r'_+', '_', safe_name)  # Collapse multiple underscores
    safe_name = safe_name.strip('_')           # Remove leading/trailing underscores
    
    # Ensure minimum length
    if len(safe_name) < 3:
        safe_name = f"resume_{safe_name}"
    
    return safe_name + extension


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def generate_unique_filename(original_name: str, prefix: str = "") -> str:
    """
    Generate a unique filename with timestamp and sanitization.
    """
    from datetime import datetime
    import uuid
    
    file_path = Path(original_name)
    sanitized_stem = sanitize_filename(file_path.stem)
    extension = file_path.suffix.lower()
    
    # Create unique identifier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Combine parts
    if prefix:
        unique_name = f"{prefix}_{sanitized_stem}_{timestamp}_{unique_id}{extension}"
    else:
        unique_name = f"{sanitized_stem}_{timestamp}_{unique_id}{extension}"
    
    return unique_name


# ─── File reading helpers ─────────────────────────────────────────────────────

def safe_read_chunks(file_obj: BinaryIO, chunk_size: int = 8192):
    """
    Safely read file in chunks to avoid memory issues.
    """
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk


def detect_file_type(file_content: bytes) -> str | None:
    """
    Detect file type from magic bytes.
    Returns MIME type or None if unrecognized.
    """
    if file_content.startswith(b'%PDF'):
        return "application/pdf"
    
    # DOCX files are ZIP archives with specific structure
    if file_content.startswith(b'PK\x03\x04') and b'word/' in file_content[:1024]:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    return None