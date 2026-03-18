import os
import platform
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


# On Azure App Service (Linux), /home is a persistent Azure Files mount.
# Locally, fall back to a file in the current working directory.
_default_db = (
    "sqlite:////home/data/ai_app.db"
    if platform.system() != "Windows"
    else "sqlite:///./ai_application_improver.db"
)

DATABASE_URL = os.getenv("DATABASE_URL", _default_db)

if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    _connect_args = {"connect_timeout": 3}
else:
    _connect_args = {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
