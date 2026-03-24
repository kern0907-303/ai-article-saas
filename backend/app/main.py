import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, articles, auth, billing, images, knowledge_files, publish, settings
from app.core.config import settings as app_settings
from app.core.database import Base, engine
from app.core.migrations import run_startup_migrations

logger = logging.getLogger("uvicorn.error")

Base.metadata.create_all(bind=engine)
run_startup_migrations(engine)

app = FastAPI(title=app_settings.app_name)

allowed_origins = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "AI 文章 SaaS 後端 API 運行中"}


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "database_backend": "sqlite" if app_settings.database_url.startswith("sqlite") else "server",
        "storage_dir": str(app_settings.storage_dir),
        "persistent_storage_enabled": app_settings.persistent_storage_enabled,
    }


@app.get("/readyz")
def readyz():
    return {
        "status": "ready",
        "database_backend": "sqlite" if app_settings.database_url.startswith("sqlite") else "server",
    }


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = str(uuid4())
    start = time.perf_counter()
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time"] = f"{(time.perf_counter() - start):.4f}s"
        return response
    except Exception:
        logger.exception("Unhandled API error request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "伺服器發生未預期錯誤，請稍後再試",
                "request_id": request_id,
            },
        )


app.include_router(auth.router, prefix=app_settings.api_prefix)
app.include_router(billing.router, prefix=app_settings.api_prefix)
app.include_router(settings.router, prefix=app_settings.api_prefix)
app.include_router(knowledge_files.router, prefix=app_settings.api_prefix)
app.include_router(articles.router, prefix=app_settings.api_prefix)
app.include_router(images.router, prefix=app_settings.api_prefix)
app.include_router(publish.router, prefix=app_settings.api_prefix)
app.include_router(admin.router, prefix=app_settings.api_prefix)
