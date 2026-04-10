from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loads and validates application settings and secrets."""
    spotify_client_id: str = "YOUR_SPOTIFY_CLIENT_ID"
    spotify_client_secret: str = "YOUR_SPOTIFY_CLIENT_SECRET"
    google_api_key: str = "YOUR_GOOGLE_API_KEY"
    disney_username: str = "YOUR_DISNEY_USERNAME"
    disney_password: str = "YOUR_DISNEY_PASSWORD"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()