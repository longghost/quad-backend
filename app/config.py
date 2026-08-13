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
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_from_email: str = os.getenv("RESEND_FROM_EMAIL", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")


settings = Settings()
