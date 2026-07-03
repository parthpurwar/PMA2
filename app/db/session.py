from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

main_engine = create_engine(settings.main_database_url, connect_args={"check_same_thread": False})
temp_engine = create_engine(settings.temp_database_url, connect_args={"check_same_thread": False})

MainSessionLocal = sessionmaker(bind=main_engine, autoflush=False, autocommit=False, expire_on_commit=False)
TempSessionLocal = sessionmaker(bind=temp_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_main_db() -> Generator[Session, None, None]:
    db = MainSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_temp_db() -> Generator[Session, None, None]:
    db = TempSessionLocal()
    try:
        yield db
    finally:
        db.close()
