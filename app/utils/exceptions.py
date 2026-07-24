import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.responses import error_response

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, str(exc.detail)),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content=error_response(422, "validation error"),
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_response(500, "internal server error"),
    )
