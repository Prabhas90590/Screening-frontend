import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _sanitize_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean validation errors to ensure they are strictly JSON-serializable."""
    cleaned = []
    for err in errors:
        err_dict = {
            "type": err.get("type", "value_error"),
            "loc": list(err.get("loc", [])),
            "msg": str(err.get("msg", "Invalid value")),
            "input": str(err.get("input", "")),
        }
        cleaned.append(err_dict)
    return cleaned


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        cleaned_errors = _sanitize_errors(exc.errors())
        first_msg = cleaned_errors[0]["msg"] if cleaned_errors else "The request contains invalid data."
        # If message starts with "Value error, ", strip that prefix for cleaner user display
        if first_msg.startswith("Value error, "):
            first_msg = first_msg.replace("Value error, ", "")

        return JSONResponse(
            status_code=422,
            content={
                "detail": first_msg,
                "error": {
                    "code": "validation_error",
                    "message": first_msg,
                    "details": cleaned_errors,
                    "path": str(request.url.path),
                },
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled backend error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected server error occurred.",
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected server error occurred.",
                    "path": str(request.url.path),
                },
            },
        )
