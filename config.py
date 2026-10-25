"""Central configuration. Secrets come from the .env file (via python-dotenv)."""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "tax_system.db")
    # Some hosts still hand out "postgres://", which SQLAlchemy no longer accepts
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Razorpay (use TEST keys only: they start with "rzp_test_")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # Default admin account, created automatically on first run
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@municipal.gov")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

    # Deployment settings
    PRODUCTION = os.getenv("PRODUCTION") == "1"      # set PRODUCTION=1 on the host
    SEED_DEMO = os.getenv("SEED_DEMO") == "1"        # re-create demo data on start-up
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = PRODUCTION               # cookies only over HTTPS when deployed
