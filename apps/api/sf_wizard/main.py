from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sf_wizard.api.health import router as health_router
from sf_wizard.api.orgs import router as orgs_router
from sf_wizard.api.query import router as query_router
from sf_wizard.api.runs import router as runs_router

app = FastAPI(title="SF Wizard API", version="0.1.0")

# Local dev convenience: allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(orgs_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
