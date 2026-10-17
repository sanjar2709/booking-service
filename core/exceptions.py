import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Every error leaves the API in the same shape:
# {"error": {"code": "not_found", "message": "Booking not found", "details": null}}


def error_response(status_code: int, message: str, details=None, headers=None) -> JSONResponse:
    code = HTTPStatus(status_code).phrase.lower().replace(' ', '_').replace('-', '_')
    return JSONResponse(
        status_code=status_code,
        content={'error': {'code': code, 'message': message, 'details': details}},
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(exc.status_code, str(exc.detail), headers=getattr(exc, 'headers', None))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {'field': '.'.join(str(part) for part in err['loc'] if part != 'body'), 'message': err['msg']}
        for err in exc.errors()
    ]
    return error_response(422, 'Invalid request data', details)


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception('Unhandled error on %s %s', request.method, request.url.path)
    return error_response(500, 'Something went wrong on our side')


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
