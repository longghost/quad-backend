import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expires_days: int = 7
    cors_origin: str = os.getenv("CORS_ORIGIN", "*")
    upload_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    paystack_secret_key: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    smtp_email: str = os.getenv("SMTP_EMAIL", "")
    smtp_app_password: str = os.getenv("SMTP_APP_PASSWORD", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")


settings = Settings()
