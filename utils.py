from functools import wraps
from flask import flash, redirect, url_for, session, current_app
from flask_login import current_user, logout_user # تم استيراد current_user هنا
import json
import os
from datetime import datetime, date
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from werkzeug.utils import secure_filename

# استيراد db فقط هنا. لا تستورد النماذج (مثل Company) في هذا المكان
from models import db 

# ALL_PERMISSIONS, ADMIN_ROLES, WEEK_DAYS لا تعتمد على db، يمكن أن تكون هنا
ALL_PERMISSIONS = {
    'manage_users': 'إدارة المستخدمين (الشركات)',
    'manage_admins': 'إدارة المديرين (صلاحيات، إضافة، تعديل، حذف)',
    'manage_appointments': 'إدارة المواعيد (قبول، رفض، تعديل)',
    'manage_files': 'إدارة ملفات الأصناف (رفع، تعطيل)',
    'send_notifications': 'إرسال إشعارات للشركات',
    'view_reports': 'عرض التقارير والإحصائيات',
    'manage_settings': 'إدارة إعدادات النظام (لوجو، نسخ احتياطي، مسح سجلات، صيانة، قيود الطلبات، إعلانات)',
    'manage_ad_images': 'إدارة الصور الإعلانات',
    'manage_community_chat': 'إدارة شات المجتمع (حذف/تثبيت رسائل، إلخ)'
}

ADMIN_ROLES = {
    'super': {
        'name': 'مدير عام',
        'permissions': ['all']
    },
    'manager': {
        'name': 'مدير',
        'permissions': ['manage_users', 'manage_appointments', 'manage_files', 'view_reports', 'send_notifications', 'manage_settings', 'manage_ad_images', 'manage_community_chat']
    },
    'editor': {
        'name': 'محرر',
        'permissions': ['manage_appointments', 'manage_files', 'send_notifications']
    },
    'viewer': {
        'name': 'مشاهد',
        'permissions': ['view_reports']
    }
}

WEEK_DAYS = {
    0: 'الأحد',
    1: 'الاثنين',
    2: 'الثلاثاء',
    3: 'الأربعاء',
    4: 'الخميس',
    5: 'الجمعة',
    6: 'السبت'
}

def check_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # تم نقل فحص current_user إلى هنا داخل الدالة المزينة
            # لضمان أنها تُنفذ فقط عندما يكون هناك طلب Flask نشط و current_user متاحًا
            if not current_user.is_authenticated:
                flash('غير مصرح لك بالوصول، يرجى تسجيل الدخول.', 'error')
                return redirect(url_for('login'))

            if session.get('user_type') != 'admin' or not current_user.is_active:
                flash('غير مصرح لك بالوصول', 'error')
                logout_user() 
                session.pop('user_type', None)
                return redirect(url_for('login'))

            user_role_permissions = ADMIN_ROLES.get(current_user.role, {}).get('permissions', [])

            user_specific_permissions = []
            if current_user.permissions:
                try:
                    user_specific_permissions = json.loads(current_user.permissions)
                except json.JSONDecodeError:
                    user_specific_permissions = []

            final_permissions = list(set(user_role_permissions + user_specific_permissions))

            if 'all' in final_permissions:
                return f(*args, **kwargs)

            if permission not in final_permissions:
                flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
                return redirect(url_for('admin_dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# دالة لـ user_loader - تستورد النماذج هنا
def load_user(user_id):
    # استيراد النماذج داخل الدالة لضمان أنها معرفة
    from models import Admin, Company 
    try:
        user_type = session.get('user_type')
        
        # إذا كان نوع المستخدم موجود في الجلسة، استخدمه مباشرة
        if user_type == 'admin':
            admin = Admin.query.get(int(user_id))
            if admin and admin.is_active:
                return admin
        elif user_type == 'company':
            company = Company.query.get(int(user_id))
            if company and company.is_active:
                return company
        
        # إذا لم يكن نوع المستخدم موجود في الجلسة (حالة Remember Me)
        # نحاول البحث في كلا الجدولين لتحديد نوع المستخدم
        if not user_type:
            # أولاً نبحث في جدول الإدارة
            admin = Admin.query.get(int(user_id))
            if admin and admin.is_active:
                # إعادة تعيين نوع المستخدم في الجلسة
                session['user_type'] = 'admin'
                return admin
            
            # إذا لم نجده في الإدارة، نبحث في جدول الشركات
            company = Company.query.get(int(user_id))
            if company and company.is_active:
                # إعادة تعيين نوع المستخدم في الجلسة
                session['user_type'] = 'company'
                return company
        
        return None
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

# دالة لـ context_processor - تستورد النماذج هنا
# تم تعديلها لتستقبل 'app' و 'db' وتوحيد مسار اللوجو
def inject_global_data(app, db): 
    # استيراد النموذج داخل الدالة لضمان أنها معرفة
    from models import SystemSetting 
    
    global_data = {}
    current_logo_path = None

    # يجب أن نكون ضمن App Context للوصول إلى قاعدة البيانات
    with app.app_context():
        logo_setting = SystemSetting.query.filter_by(setting_key='current_logo').first()
        if logo_setting and logo_setting.setting_value:
            # مسار موحد: دائماً 'static/logos/'
            current_logo_path = url_for('static', filename=f'logos/{logo_setting.setting_value}')
        else:
            # Fallback للوجو الافتراضي
            current_logo_path = url_for('static', filename='images/default_logo.png')

    global_data['current_logo_path'] = current_logo_path
    # يمكن إزالة current_logo_filename من هنا إذا لم تعد تستخدمه مباشرة في القوالب
    # global_data['current_logo_filename'] = logo_setting.setting_value if logo_setting else None

    return global_data

# دالة مساعدة لتحديد امتدادات اللوجو المسموح بها
def allowed_logo_file(filename):
    # كود هذه الدالة موجود بالفعل لديك
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_LOGO_EXTENSIONS']

# دالة مساعدة لتحديد امتدادات الصور الإعلانية المسموح بها
def allowed_image_file(filename):
    # كود هذه الدالة موجود بالفعل لديك
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'html', 'htm'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

# دالة تحديث قاعدة البيانات
def update_database_schema(app, db):
    # استيراد جميع النماذج هنا لضمان أنها معرفة عند بدء التحديث
    from models import (Admin, Company, ProductFile, Appointment, Notification, SearchLog, 
                        FavoriteProduct, SystemSetting, ProductItem, ProductStockHistory, AdImage,
                        AppDownloadLog, CommunityMessage, DbMaintenanceLog)
    try: 
        inspector = inspect(db.engine)

        # Check and add avatar column to company table
        if inspector.has_table('company'):
            columns = [col['name'] for col in inspector.get_columns('company')]
            if 'avatar' not in columns:
                print("Adding avatar column to company table...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE company ADD COLUMN avatar VARCHAR(100) DEFAULT 'male-1'"))
                    connection.commit()
                print("Avatar column added successfully!")

            if 'receive_messages_enabled' not in columns:
                print("Adding receive_messages_enabled column to company table...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE company ADD COLUMN receive_messages_enabled BOOLEAN DEFAULT 1"))
                    connection.commit()
                print("receive_messages_enabled column added successfully!")

        if inspector.has_table('community_post'):
            cp_columns = [col['name'] for col in inspector.get_columns('community_post')]
            if 'is_anonymous' not in cp_columns:
                print("Adding is_anonymous column to community_post table...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE community_post ADD COLUMN is_anonymous BOOLEAN DEFAULT 0"))
                    connection.commit()
                print("is_anonymous column added successfully!")

        tables_to_check = ['admin', 'company', 'product_file', 'appointment', 'notification', 
                           'search_log', 'favorite_product', 'system_setting', 'product_item', 
                           'product_stock_history', 'ad_image', 'app_download_log', 'community_message']

        with db.engine.connect() as connection:
            for table_name in tables_to_check:
                if not inspector.has_table(table_name):
                    print(f"Table '{table_name}' does not exist. Attempting to create.")
                    try:
                        # Create all tables
                        db.create_all()
                        break
                    except Exception as e:
                        print(f"Error creating table '{table_name}': {e}")
                        db.session.rollback() 
            
        return True, "Database updated successfully!"
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return False, f"An error occurred during database update: {str(e)}"
