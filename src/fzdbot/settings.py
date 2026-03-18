import logging
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILES = (str(REPO_ROOT / ".env"), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    discord_token: str
    server_id: int

    db_user: str
    db_password: str
    db_name: str
    db_host: str = "localhost"
    db_port: int = 3306

    log_level: str = "INFO"

    @property
    def db_config(self) -> dict[str, object]:
        return {
            "user": self.db_user,
            "password": self.db_password,
            "host": self.db_host,
            "db": self.db_name,
            "port": self.db_port,
            "autocommit": False,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
