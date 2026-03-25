# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required, logout_user
import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import json
from flask_migrate import Migrate
import logging
import rarfile
from groq import Groq
import pytz
from sqlalchemy import or_, and_, func, text, create_engine
from whitenoise import WhiteNoise

# Define CAIRO_TIMEZONE locally
CAIRO_TIMEZONE = pytz.timezone('Africa/Cairo')

# تكوين السجل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register libsql dialect for SQLAlchemy (libsql-client version)
try:
    from sqlalchemy.dialects import registry
    registry.register("sqlite.libsql", "libsql_client.sqlalchemy", "LibSQLDialect")
    registry.register("libsql", "libsql_client.sqlalchemy", "LibSQLDialect")
except Exception as e:
    logger.warning(f"Could not register libsql dialect: {e}")

# استيراد db من models.py
from models import db

# استيراد الإعدادات من config.py
try:
    from config import Config
except ImportError:
    class Config:
        SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
        STATIC_FOLDER = os.path.join(os.getcwd(), 'static')
        LOGO_FOLDER = os.path.join('static', 'logos')
        AD_IMAGES_FOLDER = os.path.join('static', 'ad_images')
        APK_FOLDER = os.path.join('static', 'apk')

def create_app():
    logger.info("Starting create_app...")
    
    instance_path = None
    if os.environ.get('VERCEL'):
        instance_path = '/tmp/instance'
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)

    template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(template_folder):
        template_folder = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__, instance_path=instance_path, template_folder=template_folder)
    app.config.from_object(Config)

    if os.path.exists('static'):
        app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

    # تهيئة SQLAlchemy مع التطبيق
    try:
        db.init_app(app)
        logger.info("DB initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DB: {e}")

    migrate = Migrate()
    migrate.init_app(app, db, render_as_batch=True)

    if not os.environ.get('VERCEL'):
        try:
            with app.app_context():
                db.create_all()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.remember_cookie_duration = timedelta(days=30)
    login_manager.session_protection = "basic"
    login_manager.remember_cookie_name = "remember_token"
    login_manager.remember_cookie_secure = app.config.get('SESSION_COOKIE_SECURE', True)
    login_manager.remember_cookie_httponly = True
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def user_loader_callback(user_id):
        return load_user(user_id)

    @app.context_processor
    def inject_global_data_callback():
        global_data = inject_global_data(app, db)
        global_data['current_user_is_authenticated'] = current_user.is_authenticated
        global_data['current_user'] = current_user
        global_data['user_is_admin'] = (current_user.is_authenticated and session.get('user_type') == 'admin')
        global_data['user_is_company'] = (current_user.is_authenticated and session.get('user_type') == 'company')
        global_data['now'] = datetime.utcnow()
        return global_data

    # Ultra-comprehensive health check for diagnosis
    @app.route('/health')
    def health_check():
        diagnosis = {
            "status": "diagnosing",
            "env": {
                "python_version": sys.version,
                "vercel": os.environ.get('VERCEL', 'No'),
                "database_url_present": bool(os.environ.get('DATABASE_URL')),
                "auth_token_present": bool(os.environ.get('DATABASE_AUTH_TOKEN'))
            },
            "steps": []
        }
        
        try:
            diagnosis["steps"].append("Checking config URI...")
            uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'None')
            diagnosis["uri_prefix"] = uri.split('?')[0] if uri else "None"
            
            diagnosis["steps"].append("Testing SQLAlchemy session...")
            with app.app_context():
                result = db.session.execute(text('SELECT 1')).fetchone()
                diagnosis["sqlalchemy_session"] = "Success: " + str(result[0])
                
            diagnosis["status"] = "healthy"
            return jsonify(diagnosis)
            
        except Exception as e:
            import traceback
            diagnosis["status"] = "error"
            diagnosis["error"] = str(e)
            diagnosis["traceback"] = traceback.format_exc()
            return jsonify(diagnosis), 200 # Return 200 so we can actually see the JSON

    # Register blueprints
    app.register_blueprint(survey_bp, url_prefix='')
    app.register_blueprint(community_bp)
    app.register_blueprint(admin_community_bp)
    app.register_blueprint(community_bonus_bp)
    app.register_blueprint(admin_db_maintenance_bp)
    app.register_blueprint(api_mobile_bp)

    register_views(app)
    register_product_reminder_routes(app)
    
    return app

# Vercel entrypoint
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
