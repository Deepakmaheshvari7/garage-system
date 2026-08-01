"""
Application configuration.

Loads all settings from environment variables. Never hardcode secrets here.
In development, values come from a local .env file (see .env.example).
In production (Render/Heroku/etc.), set these as native environment variables
in the platform's dashboard.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://garage_user:garage_pass@localhost:5432/garage_db",
    )

    # --- JWT Auth ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # --- App ---
    ENV: str = os.getenv("ENV", "development")
    STANDARD_LABOR_RATE: float = float(os.getenv("STANDARD_LABOR_RATE", "500.0"))
    TAX_PERCENTAGE: float = float(os.getenv("TAX_PERCENTAGE", "18.0"))

    # --- CORS (Streamlit frontend origin) ---
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:8501")

    def __init__(self):
        if self.ENV == "production" and not self.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not self.SECRET_KEY:
            # Dev-only fallback so the app boots without manual setup.
            # This is NEVER safe for production.
            self.SECRET_KEY = "dev-only-insecure-secret-change-me"


settings = Settings()
