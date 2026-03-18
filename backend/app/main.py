import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

from app.api.routes import generation, mcp, resume
from app.db import Base, engine
from app import db_models  # noqa: F401


app = FastAPI(title="AI Application Improver API", version="0.1.0")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api", tags=["resume"])
app.include_router(generation.router, prefix="/api", tags=["generation"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
