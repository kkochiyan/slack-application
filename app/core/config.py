from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "corp-messenger"
    app_env: str = "dev"
    debug: bool = True

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "messenger"
    postgres_user: str = "postgres"
    postgres_password: str = "password"

    database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()