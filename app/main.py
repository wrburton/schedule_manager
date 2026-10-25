"""Calendar Checklist Web Application."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from app.calendar.sync import SyncState
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.routes import auth, events, items, sync

# Configure logging
log_dir = Path.home() / ".logs" / "scheduler"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "latest.log"

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=str(log_file),
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info("Starting Calendar Checklist application")
    create_db_and_tables()
    with Session(engine) as session:
        SyncState.load(session)
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("Calendar Checklist application shut down")


app = FastAPI(
    title=settings.app_name,
    description="A web app that integrates with Google Calendar to present event-based preparation checklists",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for external access
origins = (
    ["*"]
    if settings.allowed_origins == "*"
    else [o.strip() for o in settings.allowed_origins.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RevalidatedStaticFiles(StaticFiles):
    """Static files served no-cache, so a deploy never leaves a stale app.js or
    app.css behind (the browser revalidates by etag), as in the other family apps."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Mount static files
app.mount("/static", RevalidatedStaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(items.router)
app.include_router(sync.router)


@app.get("/")
async def root(request: Request):
    """Redirect root to upcoming events."""
    rp = request.scope.get("root_path", "")
    return RedirectResponse(f"{rp}/events/upcoming")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}
