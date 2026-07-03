from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PMO Resource Management Platform"
    secret_key: str = "change-me-in-production"
    session_cookie: str = "pmo_session"
    base_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = base_dir / "data"
    main_db_path: Path = data_dir / "main.db"
    temp_db_path: Path = data_dir / "temp.db"
    cv_dir: Path = base_dir / "app" / "static" / "cvs"
    page_size: int = 12

    @property
    def main_database_url(self) -> str:
        return f"sqlite:///{self.main_db_path}"

    @property
    def temp_database_url(self) -> str:
        return f"sqlite:///{self.temp_db_path}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.cv_dir.mkdir(parents=True, exist_ok=True)
    return settings
