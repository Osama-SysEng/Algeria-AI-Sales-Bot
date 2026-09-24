from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.app.api.router import router
from backend.app.core.config import settings

app = FastAPI(title=settings.app_name, version="2.0.0", description="AI-assisted sales workspace with human approval gates")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Operator-Token"])
app.include_router(router)
app.mount("/dashboard", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "dashboard"), html=True), name="dashboard")
