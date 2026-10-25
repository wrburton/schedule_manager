"""The page templates, shared by every route module.

`rp(request)` returns the ASGI root_path (e.g. "/schedule", set by uvicorn's
--root-path behind Caddy), so templates can prefix absolute hrefs without
hardcoding it.
"""
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"


def rp(request: Request) -> str:
    """The app's root path ("" when served at /)."""
    return request.scope.get("root_path", "")


def is_htmx(request: Request) -> bool:
    """True for requests made by htmx (they get an HTML fragment back, not a redirect)."""
    return request.headers.get("HX-Request") == "true"


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["rp"] = rp
templates.env.globals["sync_minutes"] = settings.sync_interval_minutes
