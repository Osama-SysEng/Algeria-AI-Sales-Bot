import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.app.api.router import router
from backend.app.core.config import settings
from backend.app.core.logging_utils import get_logger, new_request_id, request_id_ctx

access_logger = get_logger("http.access")

app = FastAPI(title=settings.app_name, version="2.0.0", description="AI-assisted sales workspace with human approval gates")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Operator-Token"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    access_logger.info(
        f"access: {request.method} {request.url.path} -> {response.status_code}",
        extra={"fields": {
            "event": "http.access",
            "method": request.method,
            "route": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }},
    )
    return response


app.include_router(router)
app.mount("/dashboard", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "dashboard"), html=True), name="dashboard")
