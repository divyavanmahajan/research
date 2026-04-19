"""Apartment Finder Backend — FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import listing, parse_url, search, travel_times

app = FastAPI(
    title="Apartment Finder API",
    description="Stateless proxy for the Qasa GraphQL API",
    version="0.1.0",
)

# CORS configuration
allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(listing.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(parse_url.router, prefix="/api")
app.include_router(travel_times.router, prefix="/api")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
