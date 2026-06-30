from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()

_db_url = settings.database_url
# SQLAlchemy expects postgresql:// (postgres:// works on newer versions but normalize anyway)
if _db_url.startswith("postgres://"):
    _db_url = "postgresql://" + _db_url[len("postgres://") :]

connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
# Neon / managed Postgres: keep connections short-lived in serverless-friendly pools
engine_kwargs: dict = {"connect_args": connect_args}
if _db_url.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(_db_url, **engine_kwargs)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
