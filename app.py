# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required, logout_user
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import json
from flask_migrate import Migrate
import logging
import rarfile
from groq import Groq
import pytz
from sqlalchemy import or_, and_, func, text
from whitenoise import WhiteNoise

# Define CAIRO_TIMEZONE locally
CAIRO_TIMEZONE = pytz.timezone('Africa/Cairo')

# تكوين السجل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register libsql dialect for SQLAlchemy
try:
    from sqlalchemy.dialects import registry
    # Use 'sqlite.libsql' as the dialect name for libsql-experimental
    registry.register("libsql", "libsql_experimental.sqlalchemy", "LibSQLDialect")
    registry.register("sqlite.libsql", "libsql_experimental.sqlalchemy", "LibSQLDialect")
except Exception:
    pass

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

# استيراد الدوال المساعدة
from utils import update_database_schema, load_user, inject_global_data, ADMIN_ROLES, ALL_PERMISSIONS
from views import register_views
from survey_routes import survey_bp
from community_routes import community_bp
from admin_community_routes import admin_community_bp
from community_bonus_routes import community_bonus_bp
from product_reminder_routes import register_product_reminder_routes
from admin_db_maintenance_routes import admin_db_maintenance_bp
from api_mobile import api_mobile_bp

def create_app():
    logger.info("Starting create_app...")
    # Writable instance path for serverless/container environments
    instance_path = None
    if os.environ.get('VERCEL') or os.environ.get('RAILWAY_ENVIRONMENT'):
        instance_path = '/tmp/instance'
        if not os.path.exists(instance_path):
            os.makedirs(instance_path, exist_ok=True)

    # Vercel might not include empty directories or may have different root
    template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(template_folder):
        # If templates folder doesn't exist, use the current directory as fallback
        # (Since many .html files are in the root)
        template_folder = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__, instance_path=instance_path, template_folder=template_folder)
    app.config.from_object(Config)

    # Use WhiteNoise to serve static files
    if os.path.exists('static'):
        app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

    ad_images_folder = app.config.get('AD_IMAGES_FOLDER')
    if not os.path.isabs(ad_images_folder):
        ad_images_folder = os.path.join(app.root_path, ad_images_folder)
        app.config['AD_IMAGES_FOLDER'] = ad_images_folder

    # إنشاء المجلدات للتأكد من وجودها
    if not os.environ.get('VERCEL'):
        for folder in [app.config['UPLOAD_FOLDER'], app.config['LOGO_FOLDER'], app.config['AD_IMAGES_FOLDER'], app.config['APK_FOLDER']]:
            try:
                if not os.path.exists(folder):
                    os.makedirs(folder, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create folder {folder}: {e}")

    # تهيئة SQLAlchemy مع التطبيق
    try:
        logger.info(f"Initializing DB with URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        db.init_app(app)
        logger.info("DB initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DB: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Initialize Flask-Migrate
    migrate = Migrate()
    migrate.init_app(app, db, render_as_batch=True)

    # Ensure all tables exist (enabled in Railway, disabled in Vercel)
    if os.environ.get('RAILWAY_ENVIRONMENT') or not os.environ.get('VERCEL'):
        try:
            with app.app_context():
                db.create_all()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

    # إعداد نظام تسجيل الدخول
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

    @app.before_request
    def revoke_expired_premium_if_needed():
        from models import Company
        try:
            if current_user.is_authenticated and session.get('user_type') == 'company':
                if hasattr(current_user, 'is_premium') and hasattr(current_user, 'premium_end_date'):
                    if current_user.is_premium and current_user.premium_end_date and datetime.utcnow() > current_user.premium_end_date:
                        company = Company.query.get(current_user.id)
                        if company and company.is_premium and company.premium_end_date and datetime.utcnow() > company.premium_end_date:
                            company.is_premium = False
                            db.session.commit()
        except Exception:
            db.session.rollback()

    @login_manager.user_loader
    def user_loader_callback(user_id):
        return load_user(user_id)

    @app.context_processor
    def inject_global_data_callback():
        global_data = inject_global_data(app, db)

        def has_permission_for_template(permission):
            if not current_user.is_authenticated or not current_user.is_active:
                return False
            if current_user.role == 'super':
                return True
            user_role_permissions = ADMIN_ROLES.get(current_user.role, {}).get('permissions', [])
            user_specific_permissions = []
            if current_user.permissions:
                try:
                    user_specific_permissions = json.loads(current_user.permissions)
                except json.JSONDecodeError:
                    user_specific_permissions = []
            final_permissions = list(set(user_role_permissions + user_specific_permissions))
            if 'all' in final_permissions:
                return True
            return permission in final_permissions

        global_data['has_permission'] = has_permission_for_template
        global_data['current_user_is_authenticated'] = current_user.is_authenticated
        global_data['current_user'] = current_user
        global_data['user_is_admin'] = (current_user.is_authenticated and session.get('user_type') == 'admin')
        global_data['user_is_company'] = (current_user.is_authenticated and session.get('user_type') == 'company')
        global_data['now'] = datetime.utcnow()
        
        global_data['ramadan_theme_enabled'] = False
        if os.environ.get('VERCEL'):
            try:
                from models import SystemSetting
                ramadan_theme_setting = SystemSetting.query.filter_by(setting_key='ramadan_theme_enabled').first()
                if ramadan_theme_setting:
                    global_data['ramadan_theme_enabled'] = (ramadan_theme_setting.setting_value == 'true')
            except Exception as e:
                logger.error(f"Error querying ramadan_theme_enabled: {e}")
        else:
            try:
                from models import SystemSetting
                ramadan_theme_setting = SystemSetting.query.filter_by(setting_key='ramadan_theme_enabled').first()
                if ramadan_theme_setting:
                    global_data['ramadan_theme_enabled'] = (ramadan_theme_setting.setting_value == 'true')
            except Exception as e:
                logger.error(f"Error querying ramadan_theme_enabled: {e}")

        return global_data

    # Health check route
    @app.route('/health')
    def health_check():
        from models import SystemSetting
        try:
            # Try to query a simple table to verify connection
            setting = SystemSetting.query.first()
            return jsonify({
                "status": "healthy", 
                "database": "connected",
                "message": "Turso connection established",
                "data": setting.setting_key if setting else "No settings found"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "type": type(e).__name__
            }), 500

    # Register blueprints
    app.register_blueprint(survey_bp, url_prefix='')
    app.register_blueprint(community_bp)
    app.register_blueprint(admin_community_bp)
    app.register_blueprint(community_bonus_bp)
    app.register_blueprint(admin_db_maintenance_bp)
    app.register_blueprint(api_mobile_bp)

    register_views(app)
    register_product_reminder_routes(app)
    
    @app.route('/ad_images/<path:filename>')
    def serve_ad_image(filename):
        return send_from_directory(app.config['AD_IMAGES_FOLDER'], filename)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

# Vercel entrypoint
app = create_app()
