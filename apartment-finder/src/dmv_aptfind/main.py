"""Apartment Finder Backend — FastAPI application entry point."""

import importlib.resources
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import geocode, listing, parse_url, search, travel_times

app = FastAPI(
    title="Apartment Finder API",
    description="Stateless proxy for the Qasa GraphQL API",
    version="0.1.0",
)

# CORS configuration — empty string means same-origin only (no CORS needed when
# frontend is served from this process). Set ALLOWED_ORIGINS for dev proxying.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = [o for o in _origins_env.split(",") if o]

if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register API routers
app.include_router(geocode.router, prefix="/api")
app.include_router(listing.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(parse_url.router, prefix="/api")
app.include_router(travel_times.router, prefix="/api")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Serve pre-built React frontend from the static/ directory bundled in this package.
# This mount must come AFTER all /api routes.
_static_dir = importlib.resources.files("dmv_aptfind").joinpath("static")
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
