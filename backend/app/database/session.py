"""Database engine and request-scoped SQLAlchemy sessions."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import secret_value, settings

url = secret_value(settings.DATABASE_URL)
if url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url[len("postgres://"):]
elif url.startswith("postgresql://"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]

_connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 10}
_engine_options = {"pool_pre_ping": True, "connect_args": _connect_args}
if url in {"sqlite://", "sqlite:///:memory:"}:
    _engine_options["poolclass"] = StaticPool
elif url.startswith("postgresql+"):
    # Keep function instances from multiplying database connections on serverless platforms.
    _engine_options.update({"pool_size": max(1, settings.DATABASE_POOL_SIZE), "max_overflow": 0, "pool_recycle": 300})

engine = create_engine(url, **_engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
