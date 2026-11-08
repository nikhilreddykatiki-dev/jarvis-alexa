"""JARVIS Configuration — loads from .env with validation."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "JARVIS"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    log_level: str = "INFO"

    # Groq AI
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(
        default="qwen/qwen3.8-27b",
        description="Groq model ID — check availability at console.groq.com",
    )
    groq_max_tokens: int = 1024
    groq_temperature: float = 0.7

    # Database
    database_url: str = "sqlite:///./jarvis.db"

    # Alexa
    alexa_skill_id: str = ""
    alexa_verify_requests: bool = True

    # Optional integrations
    weather_api_key: Optional[str] = None
    search_api_key: Optional[str] = None

    # Rate limiting
    rate_limit_rpm: int = 30  # Groq free tier: 30 req/min
    rate_limit_rpd: int = 14400  # Groq free tier: 14400 req/day

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
