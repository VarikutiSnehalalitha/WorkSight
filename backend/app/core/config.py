import base64
import hashlib
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "WorkSight"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Primary production database is PostgreSQL.
    # For zero-config local development without a running Postgres service,
    # defaults to a local SQLite file unless DATABASE_URL is explicitly set.
    DATABASE_URL: str = "sqlite:///./worksight_dev.db"

    # Authentication
    JWT_SECRET_KEY: str = "worksight-dev-jwt-secret-replace-in-production-32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    STREAM_TOKEN_EXPIRE_MINUTES: int = 15

    # Symmetric encryption key (Fernet) for RTSP URLs and camera credentials.
    # If empty in dev, deterministically derived from JWT_SECRET_KEY (must be set explicitly in prod).
    CAMERA_ENCRYPTION_KEY: str = ""

    # Privacy & retention defaults
    DEFAULT_VIDEO_RETENTION_DAYS: int = 7
    DEFAULT_EVENT_RETENTION_DAYS: int = 90
    RECORDING_STORAGE_DIR: str = "./recordings"
    ENABLE_RAW_VIDEO_STORAGE: bool = False

    # AI Computer Vision settings
    AI_VISION_ENABLED: bool = True
    AI_MODEL_PATH: str = "yolov8n.pt"
    AI_PERSON_CONFIDENCE_THRESHOLD: float = 0.45
    AI_FRAME_SAMPLE_FPS: float = 2.0
    AI_USE_GPU: bool = False

    # Simulated feeds for development (always explicitly marked as simulated)
    ALLOW_SIMULATED_FEEDS: bool = True

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def resolved_fernet_key(self) -> bytes:
        if self.CAMERA_ENCRYPTION_KEY:
            return self.CAMERA_ENCRYPTION_KEY.encode("utf-8")
        digest = hashlib.sha256(self.JWT_SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
