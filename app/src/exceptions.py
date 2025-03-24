from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimitException(Exception):
    """Exception raised when API rate limit is exceeded"""

    def __init__(self, message: str = "Too many requests"):
        self.message = message


class ServiceUnavailableException(Exception):
    """Exception raised when service is temporarily unavailable"""

    def __init__(self, message: str = "Service temporarily unavailable"):
        self.message = message


class BadRequestException(Exception):
    """Exception raised when request is malformed or invalid"""

    def __init__(self, message: str = "Bad request"):
        self.message = message


async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableException):
    return JSONResponse(status_code=503, content={"message": exc.message})


async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    return JSONResponse(
        status_code=429,
        content={"message": exc.message},
        headers={"Retry-After": "60"},  # Retry after 60 seconds
    )
