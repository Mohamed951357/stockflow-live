import os
import secrets
from pathlib import Path
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Turso Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DATABASE_AUTH_TOKEN = os.environ.get('DATABASE_AUTH_TOKEN')
    
    if DATABASE_URL:
        # For Turso with SQLAlchemy, we use the sqlite protocol with the auth_token as a query parameter.
        # SQLAlchemy will use the sqlite3 driver, and libsql-experimental provides the necessary extensions.
        if DATABASE_URL.startswith('libsql://'):
            # Replace libsql:// with sqlite://
            base_url = DATABASE_URL.replace('libsql://', 'sqlite:///')
            if DATABASE_AUTH_TOKEN:
                # Append auth_token for Turso authentication
                SQLALCHEMY_DATABASE_URI = f"{base_url}?auth_token={DATABASE_AUTH_TOKEN}"
            else:
                SQLALCHEMY_DATABASE_URI = base_url
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to local SQLite for development
        _default_sqlite_path = str(Path(__file__).resolve().parent.joinpath('site.db')).replace('\\', '/')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_default_sqlite_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Vercel specific: Ensure we don't try to use any local storage that's not /tmp
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    STATIC_FOLDER = 'static'
    LOGO_FOLDER = 'logos'
    AD_IMAGES_FOLDER = 'ad_images'
    APK_FOLDER = 'apk_files'

    # ===== إعدادات الجلسة والكوكيز =====
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_NAME = 'bonus_pharma_session'
    SESSION_COOKIE_HTTPONLY = True
    # Default to True on production (Vercel), False for local development
    SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() in ['true', '1', 'yes', 'on']
    SESSION_COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_PATH = '/'
    SESSION_REFRESH_EACH_REQUEST = True

    # Remember Me settings
    REMEMBER_COOKIE_NAME = 'bonus_pharma_remember'
    REMEMBER_COOKIE_DURATION = timedelta(days=60)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', os.environ.get('COOKIE_SECURE', 'true')).lower() in ['true', '1', 'yes', 'on']
    REMEMBER_COOKIE_SAMESITE = os.environ.get('REMEMBER_COOKIE_SAMESITE', os.environ.get('COOKIE_SAMESITE', 'Lax'))
    REMEMBER_COOKIE_PATH = '/'
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True

    # Flask-Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # File upload settings
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024
    ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'html', 'htm'}
