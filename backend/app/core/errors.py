"""
Aurora error codes, exception classes, and FastAPI exception handlers.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorDescriptor:
    def __init__(self, code: str, message: str, http_status: int, details: Optional[str] = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details


# ---------------------------------------------------------------------------
# Error registry
# ---------------------------------------------------------------------------
ERROR_REGISTRY: dict[str, ErrorDescriptor] = {
    # Auth errors
    "AURORA-E001": ErrorDescriptor("AURORA-E001", "Invalid credentials", 401),
    "AURORA-E002": ErrorDescriptor("AURORA-E002", "Token expired", 401),
    "AURORA-E003": ErrorDescriptor("AURORA-E003", "Token invalid", 401),
    "AURORA-E004": ErrorDescriptor("AURORA-E004", "Email already registered", 409),
    "AURORA-E005": ErrorDescriptor("AURORA-E005", "Email not verified", 403),
    "AURORA-E006": ErrorDescriptor("AURORA-E006", "Account suspended", 403),
    # Upload / audio errors
    "AURORA-E007": ErrorDescriptor("AURORA-E007", "Lossy format detected — quality may be reduced", 200),
    "AURORA-E008": ErrorDescriptor("AURORA-E008", "Unsupported audio format", 415),
    "AURORA-E009": ErrorDescriptor("AURORA-E009", "File too large (max 500 MB)", 413),
    "AURORA-E010": ErrorDescriptor("AURORA-E010", "Audio too short (minimum 2 seconds)", 422),
    "AURORA-E011": ErrorDescriptor("AURORA-E011", "Invalid sample rate", 422),
    "AURORA-E012": ErrorDescriptor("AURORA-E012", "Invalid channel count", 422),
    # Render errors
    "AURORA-E301": ErrorDescriptor("AURORA-E301", "Render timed out", 504),
    "AURORA-E302": ErrorDescriptor("AURORA-E302", "Render job not found", 404),
    "AURORA-E303": ErrorDescriptor("AURORA-E303", "Render job already completed", 409),
    "AURORA-E304": ErrorDescriptor("AURORA-E304", "Render slot limit reached", 429),
    # Session errors
    "AURORA-E401": ErrorDescriptor("AURORA-E401", "Session not found", 404),
    "AURORA-E402": ErrorDescriptor("AURORA-E402", "Session access denied", 403),
    # Storage errors
    "AURORA-E601": ErrorDescriptor("AURORA-E601", "Storage quota exceeded", 507),
    "AURORA-E602": ErrorDescriptor("AURORA-E602", "Invalid storage key ownership", 403),
    "AURORA-E603": ErrorDescriptor("AURORA-E603", "Object not found in storage", 404),
    # Billing errors
    "AURORA-E701": ErrorDescriptor("AURORA-E701", "Stripe error", 502),
    "AURORA-E702": ErrorDescriptor("AURORA-E702", "Subscription not found", 404),
    "AURORA-E703": ErrorDescriptor("AURORA-E703", "Invalid webhook signature", 400),
    # Generic
    "AURORA-E900": ErrorDescriptor("AURORA-E900", "Internal server error", 500),
    "AURORA-E901": ErrorDescriptor("AURORA-E901", "Not found", 404),
    "AURORA-E902": ErrorDescriptor("AURORA-E902", "Validation error", 422),
    # Business / tier gate errors
    "AURORA-B001": ErrorDescriptor("AURORA-B001", "Feature not available on your plan", 403),
    "AURORA-B002": ErrorDescriptor("AURORA-B002", "Track quota exceeded for this billing period", 429),
    "AURORA-B003": ErrorDescriptor("AURORA-B003", "Storage quota exceeded", 507),
    "AURORA-B004": ErrorDescriptor("AURORA-B004", "Export format not available on your plan", 403),
    "AURORA-B005": ErrorDescriptor("AURORA-B005", "Subscription required", 402),
}


class AuroraHTTPException(Exception):
    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        details: Any = None,
        status_code: Optional[int] = None,
    ):
        descriptor = ERROR_REGISTRY.get(code)
        self.code = code
        self.message = message or (descriptor.message if descriptor else "Unknown error")
        self.details = details
        self.status_code = status_code or (descriptor.http_status if descriptor else 500)
        super().__init__(self.message)


async def aurora_exception_handler(request: Request, exc: AuroraHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logging.getLogger("aurora").exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "AURORA-E900",
                "message": "Internal server error",
                "details": None,
            }
        },
    )
