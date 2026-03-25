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
        # For Turso with SQLAlchemy, we use sqlite.libsql://
        if DATABASE_URL.startswith('libsql://'):
            base_url = DATABASE_URL.replace('libsql://', 'sqlite.libsql://')
            if DATABASE_AUTH_TOKEN and 'auth_token=' not in base_url:
                separator = '&' if '?' in base_url else '?'
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
    
    # Storage settings
    # On Railway, we can use local folders if they are part of the repo, 
    # but for uploads we might want to use /tmp or a persistent volume.
    # For now, let's stick to /tmp for simplicity if not in local dev.
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
        
    STATIC_FOLDER = 'static'
    LOGO_FOLDER = 'logos'
    AD_IMAGES_FOLDER = 'ad_images'
    APK_FOLDER = 'apk_files'

    # ===== إعدادات الجلسة والكوكيز =====
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_NAME = 'bonus_pharma_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    SESSION_REFRESH_EACH_REQUEST = True

    # Remember Me settings
    REMEMBER_COOKIE_NAME = 'bonus_pharma_remember'
    REMEMBER_COOKIE_DURATION = timedelta(days=60)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
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
