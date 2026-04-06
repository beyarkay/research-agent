import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.listings import router as listings_router
from app.api.projects import router as projects_router
from app.api.requirements import router as requirements_router
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield


app = FastAPI(title="Claude Research Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api")
app.include_router(listings_router, prefix="/api")
app.include_router(requirements_router, prefix="/api")

# Serve frontend: static assets at /assets/*, and index.html for all other
# non-API routes (SPA client-side routing fallback)
_frontend_path = Path(os.path.abspath(settings.frontend_dir))
if _frontend_path.is_dir():
    _index_html = _frontend_path / "index.html"

    # Serve JS/CSS/images from /assets/
    app.mount("/assets", StaticFiles(directory=str(_frontend_path / "assets")), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(path: str) -> FileResponse:
        # Serve the actual file if it exists (e.g. favicon.ico)
        file_path = _frontend_path / path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html for client-side routing
        return FileResponse(str(_index_html))
