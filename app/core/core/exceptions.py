from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# ─── Custom exception classes ─────────────────────────────────────────────────

class AppError(Exception):
    """Base application error."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            code=f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
            message=f"{resource} could not be found.",
            status_code=404,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(code="CONFLICT", message=message, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422)


class StorageError(AppError):
    def __init__(self, message: str = "File storage operation failed."):
        super().__init__(code="STORAGE_ERROR", message=message, status_code=500)


class ProcessingError(AppError):
    def __init__(self, message: str = "Processing failed."):
        super().__init__(code="PROCESSING_ERROR", message=message, status_code=500)


# ─── Error response builder ───────────────────────────────────────────────────

def _error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


# ─── Exception handlers ───────────────────────────────────────────────────────

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, str(exc.detail)),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    details = [
        {"field": " → ".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
        for e in errors
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", "Request validation failed.", details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never expose internal details to clients
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
    )
