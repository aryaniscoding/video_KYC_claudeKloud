from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    session_token_ttl_seconds: int = 86400

    # Admin
    admin_default_email: str = "admin@poonawalla.com"
    admin_default_password: str = "changeme123"

    # LiveKit
    livekit_host: str = "http://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret"

    # Groq
    groq_api_key: str
    groq_llm_model: str = "openai/gpt-oss-20b"

    # AWS Rekognition
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"

    # GeoIP
    geoip_db_path: str = "/app/data/geoip/GeoLite2-City.mmdb"

    # SES
    ses_from_email: str = "noreply@example.com"

    # Storage
    storage_bucket_recordings: str = "kyc-recordings"
    storage_bucket_pdfs: str = "kyc-pdfs"

    # App
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
