import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.api_v1.api import api_router
from app.api.utils import get_logger
from app.core.config import settings
import json


logger = get_logger()

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Trailing slash bug for origins: https://github.com/pydantic/pydantic/issues/7186
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests and responses.
    """
    idem = "".join(str(uuid4()))
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)
    if response.status_code >= 400:
        # Capture the response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Log the response body
        logger.error(f"rid={idem} error response: {response_body.decode('utf-8', errors='ignore')}")
        
        # Recreation of response is needed since body_iterator is consumed
        from fastapi.responses import Response as FastAPIResponse
        response = FastAPIResponse(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    logger.info(
        f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
    )

    return response


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Handle validation errors.
    """
    error = exc.errors()[0]
    error_ctx = error.get("ctx", {})
    error_message = error_ctx.get("error", error["msg"])
    error_message = str(error_message)

    return JSONResponse(
        status_code=400,
        content={"detail": error_message},
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    """
    Handle ValueError exceptions.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.get("/health")
async def heart_beat():
    return JSONResponse(content="ok")


app.include_router(api_router, prefix=settings.API_V1_STR)
