from flask import Blueprint, request, jsonify, session, current_app, url_for
from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import pytz
from models import db, Company, ProductStockHistory, Appointment, Notification, NotificationRead, FavoriteProduct, SystemSetting, CommunityMessage, PrivateMessage, Admin
from sqlalchemy import or_, and_, desc

api_bp = Blueprint('api', __name__, url_prefix='/api')

CAIRO_TIMEZONE = pytz.timezone('Africa/Cairo')

@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No input data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    remember_me = data.get('remember_me', False)

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400

    # Only allow company login for now as per requirement "connect website with mobile application" for companies
    user = Company.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        if user.is_active:
            session['user_type'] = 'company'
            login_user(user, remember=remember_me, duration=timedelta(days=60) if remember_me else None)
            
            if remember_me:
                session.permanent = True
            
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'company_name': user.company_name,
                    'email': user.email,
                    'phone': user.phone,
                    'avatar': user.avatar
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Account is inactive'}), 403
    
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@api_bp.route('/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@api_bp.route('/company/dashboard', methods=['GET'])
@login_required
def get_dashboard_data():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Gather dashboard stats
    # 1. Unread notifications
    unread_notifications_count = Notification.query.filter(
        or_(
            Notification.target_type == 'all',
            and_(Notification.target_type == 'specific', Notification.target_id == current_user.id)
        ),
        Notification.is_active == True,
        ~db.session.query(NotificationRead.id).filter(
            NotificationRead.notification_id == Notification.id,
            NotificationRead.company_id == current_user.id
        ).exists()
    ).count()

    # 2. Favorite products count
    favorites_count = FavoriteProduct.query.filter_by(company_id=current_user.id).count()

    # 3. Pending appointments
    pending_appointments = Appointment.query.filter_by(company_id=current_user.id, status='pending').count()

    # 4. Unread messages (Community/Private) - simplified logic
    # This might need adjustment based on exact logic in views.py
    
    return jsonify({
        'company_name': current_user.company_name,
        'unread_notifications': unread_notifications_count,
        'favorites_count': favorites_count,
        'pending_appointments': pending_appointments,
        'is_premium': current_user.is_premium,
        'premium_end_date': current_user.premium_end_date.isoformat() if current_user.premium_end_date else None
    })

@api_bp.route('/company/profile', methods=['GET'])
@login_required
def get_profile():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'company_name': current_user.company_name,
        'email': current_user.email,
        'phone': current_user.phone,
        'avatar': current_user.avatar,
        'is_active': current_user.is_active,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    })

@api_bp.route('/company/my_products', methods=['GET'])
@login_required
def get_my_products():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
        
    favorites = FavoriteProduct.query.filter_by(company_id=current_user.id).order_by(FavoriteProduct.last_modified.desc()).all()
    
    products_data = []
    for fav in favorites:
        # Get latest stock info
        stock_record = ProductStockHistory.query.filter_by(product_name=fav.product_name)\
            .order_by(ProductStockHistory.record_date.desc(), ProductStockHistory.recorded_at.desc()).first()
            
        products_data.append({
            'id': fav.id,
            'product_name': fav.product_name,
            'quantity': fav.quantity, # This is the quantity the company "has" or "wants"? In FavoriteProduct it seems to be user defined.
            'current_stock': stock_record.quantity if stock_record else None,
            'price': stock_record.price if stock_record else fav.price,
            'notes': fav.notes,
            'last_modified': fav.last_modified.isoformat() if fav.last_modified else None
        })
        
    return jsonify(products_data)

@api_bp.route('/company/appointments', methods=['GET'])
@login_required
def get_appointments():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
        
    appointments = Appointment.query.filter_by(company_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
    
    appointments_data = []
    for appt in appointments:
        appointments_data.append({
            'id': appt.id,
            'date': appt.appointment_date.isoformat(),
            'time': appt.appointment_time.strftime('%H:%M'),
            'purpose': appt.purpose,
            'product_item_name': appt.product_item_name,
            'status': appt.status,
            'admin_response': appt.admin_response,
            'created_at': appt.created_at.isoformat()
        })
        
    return jsonify(appointments_data)

@api_bp.route('/company/notifications', methods=['GET'])
@login_required
def get_notifications():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Fetch notifications targeted to all or specific to this company
    notifications = Notification.query.filter(
        or_(
            Notification.target_type == 'all',
            and_(Notification.target_type == 'specific', Notification.target_id == current_user.id)
        ),
        Notification.is_active == True
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    notif_data = []
    for notif in notifications:
        is_read = db.session.query(NotificationRead.id).filter(
            NotificationRead.notification_id == notif.id,
            NotificationRead.company_id == current_user.id
        ).first() is not None
        
        notif_data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'created_at': notif.created_at.isoformat(),
            'is_read': is_read
        })
        
    return jsonify(notif_data)

@api_bp.route('/company/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403

    notification = Notification.query.get_or_404(notification_id)
    
    # Check if already read
    existing_read = NotificationRead.query.filter_by(
        notification_id=notification_id,
        company_id=current_user.id
    ).first()
    
    if not existing_read:
        new_read = NotificationRead(notification_id=notification_id, company_id=current_user.id)
        db.session.add(new_read)
        db.session.commit()
        
    return jsonify({'success': True})

@api_bp.route('/company/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'POST':
        data = request.get_json()
        if not data:
             return jsonify({'success': False, 'message': 'No data provided'}), 400
             
        allow_messages = data.get('allow_messages_from_companies')
        if allow_messages is not None:
            # allow_messages should be boolean
            current_user.receive_messages_enabled = bool(allow_messages)
            try:
                db.session.commit()
                return jsonify({'success': True, 'message': 'Settings updated successfully'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET request
    system_subtitle_setting = SystemSetting.query.filter_by(setting_key='system_subtitle').first()
    system_subtitle = system_subtitle_setting.setting_value if system_subtitle_setting else 'نظام حجز المواعيد وإدارة الأرصدة المتكامل'
    
    current_logo_setting = SystemSetting.query.filter_by(setting_key='current_logo').first()
    current_logo_url = url_for('static', filename=f'logos/{current_logo_setting.setting_value}') if current_logo_setting and current_logo_setting.setting_value else None
    
    return jsonify({
        'receive_messages_enabled': current_user.receive_messages_enabled,
        'system_subtitle': system_subtitle,
        'current_logo_url': current_logo_url
    })

@api_bp.route('/company/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    if session.get('user_type') != 'company':
        return jsonify({'success': False, 'message': 'غير مصرح لك بحجز المواعيد.'}), 403

    maintenance_mode_setting = SystemSetting.query.filter_by(setting_key='maintenance_mode').first()
    if maintenance_mode_setting and maintenance_mode_setting.setting_value == 'true':
        allow_company_during_maintenance = session.get('allow_company_login_during_maintenance', False)
        is_admin_testing = session.get('is_admin_logged', False)
        is_company_test_mode_session = session.get('company_test_mode', False)
        if not (allow_company_during_maintenance or is_admin_testing or is_company_test_mode_session):
            return jsonify({'success': False, 'message': 'الموقع قيد الصيانة حالياً. لا يمكن حجز المواعيد.'}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        appointment_date_str = data.get('appointment_date')
        appointment_time_str = data.get('appointment_time')
        purpose = data.get('purpose', '').strip()
        product_item_name = data.get('product_item_name', '').strip()
        phone_number = data.get('phone_number', '').strip()
        notes = data.get('notes', '').strip()
        collection_amount_str = str(data.get('collection_amount', '')).strip() # Ensure string for strip

        if not all([appointment_date_str, appointment_time_str, purpose, product_item_name, phone_number]):
            return jsonify({'success': False, 'message': 'يرجى تزويد جميع المعلومات المطلوبة (التاريخ، الوقت، الغرض، الصنف، رقم الموبايل).'}), 400

        appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(appointment_time_str, '%H:%M').time()
        
        collection_amount = None
        if collection_amount_str and collection_amount_str.lower() != 'none' and collection_amount_str != '':
             try:
                 collection_amount = float(collection_amount_str)
             except ValueError:
                 pass

        if appointment_date < date.today():
            return jsonify({'success': False, 'message': 'لا يمكن حجز موعد في تاريخ ماضٍ.'}), 400

        min_time = time(10, 0)
        max_time = time(16, 0)
        if not (min_time <= appointment_time <= max_time):
            return jsonify({'success': False, 'message': 'المواعيد متاحة فقط من الساعة 10:00 صباحاً حتى 04:00 عصراً.'}), 400

        disabled_days_setting = SystemSetting.query.filter_by(setting_key='disabled_days').first()
        disabled_days_list = []
        if disabled_days_setting and disabled_days_setting.setting_value:
            try:
                disabled_days_list = json.loads(disabled_days_setting.setting_value)
            except json.JSONDecodeError:
                disabled_days_list = []
        if str(appointment_date.weekday()) in disabled_days_list:
            disabled_days_message_setting = SystemSetting.query.filter_by(setting_key='disabled_days_message').first()
            disabled_days_message = disabled_days_message_setting.setting_value if disabled_days_message_setting else 'عذراً، هذا اليوم معطل لتلقي الطلبات.'
            return jsonify({'success': False, 'message': disabled_days_message}), 400

        max_daily_requests_setting = SystemSetting.query.filter_by(setting_key='max_daily_requests').first()
        max_daily_requests = int(max_daily_requests_setting.setting_value) if max_daily_requests_setting and max_daily_requests_setting.setting_value.isdigit() else 10

        today_appointments_count = Appointment.query.filter(
            Appointment.appointment_date == date.today(),
            Appointment.status != 'rejected'
        ).count()
        if today_appointments_count >= max_daily_requests:
            return jsonify({'success': False, 'message': f'عذراً، لقد تم الوصول للحد الأقصى من طلبات المواعيد لهذا اليوم ({max_daily_requests} موعد). يرجى المحاولة في يوم آخر.'}), 400

        if not phone_number.startswith('01') or len(phone_number) != 11 or not phone_number.isdigit():
            return jsonify({'success': False, 'message': 'يرجى إدخال رقم موبايل صحيح مكون من 11 رقم ويبدأ بـ 01.'}), 400

        new_appointment = Appointment(
            company_id=current_user.id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            purpose=purpose,
            product_item_name=product_item_name,
            notes=notes if notes else None,
            collection_amount=collection_amount,
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(new_appointment)
        db.session.commit()

        admin_notification = Notification(
            title=f'طلب موعد جديد من {current_user.company_name} عبر توبي',
            message=f'الشركة {current_user.company_name} طلبت موعداً بتاريخ {appointment_date_str} الساعة {appointment_time_str} لغرض: {purpose}. الصنف: {product_item_name}.',
            target_type='all',
            created_by=None, # Assuming this is accepted by DB as per views.py usage
            created_at=datetime.utcnow()
        )
        db.session.add(admin_notification)
        db.session.commit()

        return jsonify({'success': True, 'message': 'تم إرسال طلب الموعد بنجاح. سيتم مراجعته من قبل الإدارة قريباً.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'حدث خطأ داخلي أثناء حجز الموعد: {str(e)}'}), 500
