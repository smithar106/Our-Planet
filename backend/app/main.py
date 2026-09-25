"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.config import settings
from app.logging import setup_logging

setup_logging()
logger = logging.getLogger("planet.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PLANET starting (env=%s)", settings.environment)
    yield
    from app.db import dispose_db

    await dispose_db()


app = FastAPI(
    title="PLANET — Live Earth Intelligence",
    version=__version__,
    description="An AI agent watching Earth. Public read-only API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {"name": "PLANET", "tagline": "An AI agent watching Earth.", "version": __version__}
