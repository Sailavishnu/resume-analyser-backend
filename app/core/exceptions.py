"""
Custom exceptions and exception handlers for the application.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    """Resource not found exception."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppError):
    """Validation error exception."""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=400)


class UnauthorizedError(AppError):
    """Unauthorized access exception."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    """Forbidden access exception."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ConflictError(AppError):
    """Conflict exception (duplicate resource)."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class StorageError(AppError):
    """Storage/file operation error exception."""
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message, status_code=500)


class BadRequestError(AppError):
    """Bad request exception."""
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=400)


class ProcessingError(AppError):
    """Processing/computation error exception."""
    def __init__(self, message: str = "Processing failed"):
        super().__init__(message, status_code=500)


# Exception handlers

async def app_error_handler(request: Request, exc: AppError):
    """Handle custom application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "data": None
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation failed",
            "data": {"errors": errors}
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    import traceback
    
    # Log the error (in production, use proper logging)
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "data": None
        }
    )
