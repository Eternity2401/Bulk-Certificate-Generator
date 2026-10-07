"""
Main FastAPI Application Entrypoint.
Configures database startup, static asset mounting, HTML dashboard routing,
CORS middleware, and API v1 endpoints.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from app.db.database import init_db
from app.api.routes import router as certificates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade, lightweight Bulk Certificate Generator API. "
        "Accepts bulk recipient requests, validates data, generates ReportLab "
        "PDF certificates with embedded QR codes, tracks real-time background progress, "
        "and provides single & ZIP batch downloads."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration (allows frontend or external clients to connect smoothly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
static_dir = settings.BASE_DIR / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))

# Register API routers
app.include_router(certificates_router)


@app.get("/", response_class=HTMLResponse, summary="Interactive Web Dashboard")
async def serve_dashboard(request: Request):
    """Renders the lightweight, modern interactive generator dashboard."""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/health", summary="Service Health Check")
async def health_check():
    """System health endpoint for uptime checks (Render/Railway/Kubernetes)."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
