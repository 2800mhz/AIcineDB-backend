"""
Environment Configuration Management for AIcineDB Backend
Uses Pydantic Settings for type-safe configuration with validation
"""
import os
from typing import List, Optional
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for type-safe configuration management.
    Secrets are wrapped with SecretStr to prevent accidental logging.
    """
    
    # Environment
    ENV: str = Field(default="development", description="Environment (development/production)")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Application
    APP_NAME: str = Field(default="AIcineDB Backend", description="Application name")
    APP_VERSION: str = Field(default="2.0.0", description="Application version")
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8000, description="API server port")
    
    # Database
    DATABASE_URL: SecretStr = Field(
        description="PostgreSQL connection URL with pgvector"
    )
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: SecretStr) -> SecretStr:
        """Validate DATABASE_URL format"""
        url = v.get_secret_value()
        if not url.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must start with postgresql:// or postgres://")
        if "@" not in url or "/" not in url.split("@")[-1]:
            raise ValueError("DATABASE_URL must include credentials and database name")
        return v
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for Celery"
    )
    
    # Supabase
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL"
    )
    SUPABASE_SERVICE_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Supabase service role key (backend only)"
    )
    
    # API Keys
    GEMINI_API_KEY: SecretStr = Field(
        description="Google Gemini API key for narrative analysis"
    )
    OPENAI_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key (optional, for embeddings)"
    )
    
    # Security
    JWT_SECRET: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="JWT secret for token signing"
    )
    ADMIN_EMAIL: Optional[str] = Field(
        default=None,
        description="Primary admin email"
    )
    ADMIN_EMAILS: Optional[str] = Field(
        default=None,
        description="Comma-separated list of admin emails"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:8080",
            "https://aicinedb.com",
            "https://www.aicinedb.com"
        ],
        description="Allowed CORS origins"
    )
    
    # File Storage
    OUTPUT_DIR: str = Field(
        default="./analyses",
        description="Base directory for analysis outputs"
    )
    VIDEO_CACHE_DIR: str = Field(
        default="./data/videos",
        description="Video cache directory"
    )
    MAX_VIDEO_SIZE_MB: int = Field(
        default=500,
        description="Maximum video size in MB"
    )
    
    # Analysis Settings
    WHISPER_MODEL: str = Field(
        default="base",
        description="Whisper model size (tiny/base/small/medium/large)"
    )
    FRAME_EXTRACTION_FPS: float = Field(
        default=1.0,
        description="Frame extraction FPS"
    )
    CHARACTER_DETECTION_FPS: float = Field(
        default=2.0,
        description="Character detection FPS"
    )
    
    # Celery
    CELERY_WORKER_CONCURRENCY: int = Field(
        default=2,
        description="Celery worker concurrency"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=7200,
        description="Celery task hard time limit (seconds)"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=6000,
        description="Celery task soft time limit (seconds)"
    )
    
    # Scraping & Content Aggregation
    SCRAPING_USER_AGENT: str = Field(
        default="AICineDB Bot/1.0",
        description="User agent for web scraping"
    )
    SCRAPING_RATE_LIMIT_DELAY: int = Field(
        default=2,
        description="Delay between scraping requests (seconds)"
    )
    SCRAPING_MAX_RETRIES: int = Field(
        default=3,
        description="Maximum retries for failed scraping requests"
    )
    
    # AI Filtering
    AI_FILTER_ENABLED: bool = Field(
        default=True,
        description="Enable AI filtering for content"
    )
    AI_RELEVANCE_THRESHOLD_FESTIVALS: int = Field(
        default=60,
        description="AI relevance threshold for festivals (0-100)"
    )
    AI_RELEVANCE_THRESHOLD_NEWS: int = Field(
        default=70,
        description="AI relevance threshold for news (0-100)"
    )
    DUPLICATE_SIMILARITY_THRESHOLD: float = Field(
        default=0.95,
        description="Similarity threshold for duplicate detection (0-1)"
    )
    
    # Monitoring
    FLOWER_PORT: int = Field(
        default=5555,
        description="Flower monitoring port"
    )
    FLOWER_BASIC_AUTH: Optional[str] = Field(
        default=None,
        description="Flower basic auth (user:password)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars not defined in schema
    )
    
    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment setting"""
        allowed = ["development", "production", "staging", "testing"]
        if v not in allowed:
            raise ValueError(f"ENV must be one of: {allowed}")
        return v
    
    @field_validator("DEBUG")
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        """Force DEBUG=False in production"""
        env = info.data.get("ENV", "development")
        if env == "production" and v is True:
            raise ValueError("DEBUG must be False in production environment")
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(v, str):
            # Parse comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    def get_admin_emails(self) -> List[str]:
        """Get all configured admin emails"""
        emails = []
        
        if self.ADMIN_EMAIL:
            emails.append(self.ADMIN_EMAIL.lower())
        
        if self.ADMIN_EMAILS:
            emails.extend([
                email.strip().lower()
                for email in self.ADMIN_EMAILS.split(",")
                if email.strip()
            ])
        
        return list(set(emails))  # Remove duplicates
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENV == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENV == "development"
    
    @property
    def docs_enabled(self) -> bool:
        """Check if API docs should be enabled"""
        # Hide docs in production unless explicitly enabled
        return not self.is_production or self.DEBUG


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Loads settings once and caches for subsequent calls.
    
    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for testing
def reset_settings():
    """Reset settings singleton (useful for testing)"""
    global _settings
    _settings = None
