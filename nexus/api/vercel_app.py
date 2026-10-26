"""Deployment entrypoint: the same API mounted under /api (Vercel Services pass the original /api/... path)."""
from fastapi import FastAPI

from nexus.api.app import app as core

app = FastAPI(title="NEXUS // WORLD", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", core)
