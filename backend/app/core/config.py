import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/kyiv_events",
        validation_alias="DATABASE_URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )

    # Telegram Configurations
    TELEGRAM_BOT_TOKEN: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: str = Field(default="", validation_alias="TELEGRAM_CHANNEL_ID")
    TELEGRAM_API_ID: Optional[int] = Field(default=None, validation_alias="TELEGRAM_API_ID")
    TELEGRAM_API_HASH: Optional[str] = Field(default=None, validation_alias="TELEGRAM_API_HASH")

    # AI Processor
    AI_PROVIDER: str = Field(default="openai", validation_alias="AI_PROVIDER")
    OPENAI_API_KEY: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, validation_alias="DEEPSEEK_API_KEY")

    # Admin Settings
    ADMIN_EMAIL: str = Field(default="admin@kyivevents.com", validation_alias="ADMIN_EMAIL")
    ADMIN_PASSWORD: str = Field(default="adminpassword123", validation_alias="ADMIN_PASSWORD")
    SECRET_KEY: str = Field(default="change_this_to_something_secure_and_keep_it_secret", validation_alias="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=11520, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES") # default 8 days

    # Crawler Settings
    APP_BASE_URL: str = Field(default="http://localhost:8000", validation_alias="APP_BASE_URL")
    CRAWLER_USER_AGENT: str = Field(default="KyivEventGuideCrawler/1.0", validation_alias="CRAWLER_USER_AGENT")
    PORT: int = Field(default=8000, validation_alias="PORT")
    AUTO_PUBLISH: bool = Field(default=True, validation_alias="AUTO_PUBLISH")
    # Minimum quality score to auto-publish to channel (0-100)
    AUTO_PUBLISH_MIN_SCORE: int = Field(default=65, validation_alias="AUTO_PUBLISH_MIN_SCORE")
    # Max posts per day to prevent spam
    MAX_POSTS_PER_DAY: int = Field(default=8, validation_alias="MAX_POSTS_PER_DAY")

    # Facebook Scraper Credentials
    FACEBOOK_EMAIL: Optional[str] = Field(default=None, validation_alias="FACEBOOK_EMAIL")
    FACEBOOK_PASSWORD: Optional[str] = Field(default=None, validation_alias="FACEBOOK_PASSWORD")
    FB_TARGET_GROUPS: Optional[str] = Field(default=None, validation_alias="FB_TARGET_GROUPS")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        # For Alembic or sync scripts, we need standard postgresql:// or sqlite://
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url

# Load settings singleton
settings = Settings()
