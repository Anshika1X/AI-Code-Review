import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')


class Config:
    """Application configuration for development, testing, and production."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'development-secret-key-replace-in-production-min32bytes')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-replace-in-production-minimum-32-chars-long')
    JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24))

    # Database configuration
    # Supports PostgreSQL (via DATABASE_URL on Render/Neon/Supabase)
    # Automatically falls back to local SQLite if DATABASE_URL is not set
    raw_db_url = os.getenv('DATABASE_URL')
    if raw_db_url:
        # Normalize legacy postgres:// URI scheme to postgresql:// for SQLAlchemy 2.0
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        # Default local SQLite database for effortless fresher setup
        sqlite_path = BASE_DIR / 'ai_code_review.db'
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{sqlite_path.as_posix()}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # External APIs & Security
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    FRONTEND_URL = os.getenv('FRONTEND_URL', '*')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')


class TestConfig(Config):
    """Test configuration using in-memory SQLite database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    GEMINI_API_KEY = 'test-gemini-key'
    JWT_SECRET_KEY = 'test-jwt-secret-minimum-32-bytes-length-key'
