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
        # For Turso on Vercel with SQLAlchemy, we use sqlite.libsql:// and register the dialect
        if DATABASE_URL.startswith('libsql://'):
            base_url = DATABASE_URL.replace('libsql://', 'sqlite.libsql://')
            if DATABASE_AUTH_TOKEN and 'auth_token=' not in DATABASE_URL:
                separator = '&' if '?' in DATABASE_URL else '?'
                SQLALCHEMY_DATABASE_URI = f"{base_url}{separator}auth_token={DATABASE_AUTH_TOKEN}"
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
    UPLOAD_FOLDER = '/tmp/uploads'
    STATIC_FOLDER = 'static'
    LOGO_FOLDER = 'logos'
    AD_IMAGES_FOLDER = 'ad_images'
    APK_FOLDER = 'apk_files'

    # ===== إعدادات الجلسة والكوكيز =====
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_NAME = 'bonus_pharma_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    SESSION_REFRESH_EACH_REQUEST = True

    # Remember Me settings
    REMEMBER_COOKIE_NAME = 'bonus_pharma_remember'
    REMEMBER_COOKIE_DURATION = timedelta(days=60)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_PATH = '/'
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True

    # Flask-Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # File upload settings
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024
    ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'html', 'htm'}
