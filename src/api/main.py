"""FastAPI application for ai-km-service (CoreComp CRUD API).

INHERITED structure from the sibling services' api/main.py (FastAPI + lifespan +
CORS + health + uvicorn). CHANGED: the request-trace middleware (X-Request-ID
header + {detail, request_id} error body) is ported from the ingestion service's
main.py, the lifespan manages the Postgres pool, and the four CoreComp routers
are mounted.
"""

import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import (
    manage_bucket,
    manage_bucket_details,
    manage_data_sql,
    manage_knowledge,
    manage_questions,
    manage_sql_query,
)
from src.config.settings import settings
from src.db import pool
from src.utils.logger import get_logger, suppress_uvicorn_access_logs

logger = get_logger(__name__)
suppress_uvicorn_access_logs(paths=("/health",))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ai-km-service ...")
    # Deployment owns schema changes. Startup only establishes the runtime pool.
    pool.init_pool()
    yield
    pool.close_pool()
    logger.info("Stopped ai-km-service")


app = FastAPI(
    title="AI Knowledge Management Service (CoreComp CRUD)",
    description="CRUD APIs over the CoreComp / NNP-RAG schema: buckets, documents, Q&A, databases & saved queries.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    """Tag every request with an 8-char X-Request-ID and log unhandled failures.

    Ported from the ingestion service so log correlation is uniform across the
    NNP backends.
    """
    path = request.url.path
    if path == "/health":
        return await call_next(request)

    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    logger.info(f"[{request_id}] {request.method} {path} started")
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(f"[{request_id}] {request.method} {path} -> {response.status_code}")
        return response
    except Exception:
        logger.exception(f"[{request_id}] {request.method} {path} unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error (request_id={request_id})",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )


@app.get("/", tags=["Health"])
async def root():
    return {"service": "ai-km-service", "version": "1.0.0", "status": "running"}


@app.get("/health", tags=["Health"])
async def health():
    """Fast liveness check for K8s probes (must stay lightweight)."""
    return {"status": "healthy", "service": "up"}


@app.get("/health/deep", tags=["Health"])
async def health_deep():
    """Readiness check that touches the database."""
    try:
        await run_in_threadpool(pool.ping)
        return {"status": "healthy", "database": True}
    except Exception as exc:  # noqa: BLE001
        logger.error("Deep health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": False, "error": str(exc)},
        )


app.include_router(manage_bucket.router)
app.include_router(manage_bucket_details.router)
app.include_router(manage_questions.router)
app.include_router(manage_data_sql.router)
app.include_router(manage_sql_query.router)
app.include_router(manage_knowledge.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
