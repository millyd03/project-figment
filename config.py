from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_quotes(value: str) -> str:
    if isinstance(value, str) and len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_quotes(value):
    if isinstance(value, str) and len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
    return value


class Settings(BaseSettings):
    """Loads and validates application settings and secrets."""
    spotify_client_id: str = "YOUR_SPOTIFY_CLIENT_ID"
    spotify_client_secret: Optional[str] = None
    spotify_redirect_uri: str = "http://127.0.0.1:8002/callback"
    # Redis URL used for PKCE state and short-term caches. If empty, falls back to in-memory store (dev only).
    redis_url: Optional[str] = None
    # Token encryption: either a Fernet key (44-char urlsafe base64) or a passphrase
    token_encryption_key: Optional[str] = None
    google_api_key: str = "YOUR_GOOGLE_API_KEY"
    active_model: str = "gemini-pro"

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("spotify_client_id", "spotify_client_secret", "spotify_redirect_uri", mode="before")
    def strip_quotes(cls, v):
        return _strip_quotes(v)


settings = Settings()