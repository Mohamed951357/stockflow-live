from flask import Blueprint, request, jsonify, session, current_app, url_for
from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta, date, time
import pytz
import json
import math

from sqlalchemy import or_, and_, desc, func, extract
from fuzzywuzzy import fuzz, process

from models import (
    db, Company, Admin, ProductItem, ProductStockHistory, Appointment, 
    Notification, NotificationRead, FavoriteProduct, SystemSetting, 
    CommunityPost, PostLike, PostComment, PostView, CommunityNotification, 
    PrivateMessage, PrivateMessageEditLog, 
    CompanyStatus, CompanyStatusView, CompanyStatusReaction,
    ProductReminder, Survey, Question, SurveyResponse, Answer, BlockedProduct, SearchLog, AdImage,
    CompanySurveyStatus, AdStory
)

api_mobile_bp = Blueprint('api_mobile', __name__, url_prefix='/api/mobile')

CAIRO_TIMEZONE = pytz.timezone('Africa/Cairo')

# --- CORS Support for Mobile App ---
@api_mobile_bp.after_request
def add_cors_headers(response):
    """Allow mobile app to talk to the API from any origin."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Cookie, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@api_mobile_bp.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@api_mobile_bp.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle CORS preflight requests."""
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Cookie, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response, 200


# --- Auth Endpoints ---

@api_mobile_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'يرجى إدخال البيانات المطلوبة.'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    remember_me = data.get('remember_me', False)

    if not username or not password:
        return jsonify({'success': False, 'message': 'اسم المستخدم وكلمة المرور مطلوبان.'}), 400

    user = Company.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        if user.is_active:
            session['user_type'] = 'company'
            login_user(user, remember=remember_me, duration=timedelta(days=30) if remember_me else None)
            
            if remember_me:
                session.permanent = True
            
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'message': 'تم تسجيل الدخول بنجاح.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'company_name': user.company_name,
                    'email': user.email,
                    'phone': user.phone,
                    'avatar': user.avatar,
                    'is_premium': user.is_premium
                }
            })
        else:
            return jsonify({'success': False, 'message': 'الحساب غير نشط. يرجى التواصل مع الإدارة.'}), 403
    
    return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة.'}), 401

@api_mobile_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_type', None)
    return jsonify({'success': True, 'message': 'تم تسجيل الخروج بنجاح.'})

@api_mobile_bp.route('/check_session', methods=['GET'])
def check_session():
    if current_user.is_authenticated and session.get('user_type') == 'company':
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'company_name': current_user.company_name,
                'is_premium': current_user.is_premium
            }
        })
    return jsonify({'authenticated': False}), 401

# --- Dashboard & Profile Endpoints ---

@api_mobile_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
        
    company_id = current_user.id

    # 1. Unread notifications count
    unread_notifications = Notification.query.filter(
        or_(
            Notification.target_type == 'all',
            and_(Notification.target_type == 'specific', Notification.target_id == company_id)
        ),
        Notification.is_active == True,
        ~db.session.query(NotificationRead.id).filter(
            NotificationRead.notification_id == Notification.id,
            NotificationRead.company_id == company_id
        ).exists()
    ).count()

    # 2. Unread community interactions
    unread_community = CommunityNotification.query.filter_by(
        company_id=company_id, is_read=False
    ).count()

    # 3. Unread private messages
    unread_messages = PrivateMessage.query.filter_by(
        receiver_id=company_id, is_read=False, is_deleted_by_receiver=False
    ).count()

    # 4. Pending appointments
    pending_appointments = Appointment.query.filter_by(
        company_id=company_id, status='pending'
    ).count()

    # 5. Ad Carousel & Website Announcement
    is_premium = getattr(current_user, 'is_premium', False)
    allowed_types = ['premium', 'all'] if is_premium else ['free', 'all']
    
    # Get active ad images to show in the app carousel (Directly from AdImage)
    active_ads = AdImage.query.filter(
        AdImage.is_active == True,
        AdImage.image_type.in_(allowed_types)
    ).order_by(AdImage.upload_date.desc()).all()
    
    ads_payload = []
    for ad in active_ads:
        ads_payload.append({
            'id': ad.id,
            'image': url_for('serve_ad_image', filename=ad.filename, _external=True),
            'description': ad.description or ''
        })

    # Get website announcement from SystemSetting
    company_ad_setting = SystemSetting.query.filter_by(setting_key='company_page_ad').first()
    announcement = company_ad_setting.setting_value if company_ad_setting else ''

    # 6. Monthly search statistics
    monthly_search_limit_setting = SystemSetting.query.filter_by(setting_key='monthly_search_limit').first()
    monthly_search_limit = int(monthly_search_limit_setting.setting_value) if monthly_search_limit_setting and monthly_search_limit_setting.setting_value.isdigit() else 30
    
    now = datetime.utcnow()
    monthly_search_count = SearchLog.query.filter(
        SearchLog.company_id == company_id,
        extract('year', SearchLog.search_date) == now.year,
        extract('month', SearchLog.search_date) == now.month
    ).count()

    return jsonify({
        'company_name': current_user.company_name,
        'is_premium': current_user.is_premium,
        'unread_notifications': unread_notifications,
        'unread_community': unread_community,
        'unread_messages': unread_messages,
        'pending_appointments': pending_appointments,
        'ads': ads_payload,
        'announcement': announcement,
        'search_count': monthly_search_count,
        'search_limit': monthly_search_limit
    })

@api_mobile_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'company_name': current_user.company_name,
        'email': current_user.email,
        'phone': current_user.phone,
        'avatar': current_user.avatar,
        'is_premium': current_user.is_premium,
        'premium_end_date': current_user.premium_end_date.isoformat() if current_user.premium_end_date else None,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    })

@api_mobile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    try:
        if 'email' in data:
            current_user.email = data['email']
        if 'phone' in data:
            current_user.phone = data['phone']
        if 'avatar' in data:
            current_user.avatar = data['avatar']
        if 'password' in data and data['password']:
            current_user.password = generate_password_hash(data['password'])
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم تحديث الملف الشخصي بنجاح.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Product Endpoints ---

@api_mobile_bp.route('/products/search_stats', methods=['GET'])
@login_required
def get_search_stats():
    company_id = current_user.id
    now = datetime.utcnow()
    
    # 1. Get current month search count
    monthly_search_count = SearchLog.query.filter(
        SearchLog.company_id == company_id,
        extract('year', SearchLog.search_date) == now.year,
        extract('month', SearchLog.search_date) == now.month
    ).count()
    
    # 2. Get system limit
    limit_setting = SystemSetting.query.filter_by(setting_key='monthly_search_limit').first()
    monthly_search_limit = int(limit_setting.setting_value) if limit_setting and limit_setting.setting_value.isdigit() else 30
    
    # 3. Calculate remaining
    remaining = max(0, monthly_search_limit - monthly_search_count)
    if current_user.is_premium:
        remaining = -1 # Unlimited for premium
        
    return jsonify({
        'success': True,
        'search_count': monthly_search_count,
        'search_limit': monthly_search_limit,
        'remaining_searches': remaining,
        'is_premium': current_user.is_premium,
        'message': 'عدد البحثات الشهرية'
    })

@api_mobile_bp.route('/products/suggestions', methods=['GET'])
@login_required
def get_search_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    # Get blocked product names to exclude
    blocked_names = [bp.product_name.lower() for bp in BlockedProduct.query.all()]
    
    # Filter products by query and not blocked
    suggestions = ProductItem.query.filter(
        ProductItem.name.ilike(f'%{query}%'),
        ~func.lower(ProductItem.name).in_(blocked_names)
    ).limit(10).all()
    
    # Return unique names
    unique_names = list(set([p.name for p in suggestions]))
    result_list = unique_names[:10]
    return jsonify(result_list)

@api_mobile_bp.route('/products/recent', methods=['GET'])
@login_required
def get_recent_searches():
    # Get last 3 unique searches for the current user
    recent = db.session.query(SearchLog.search_term).filter(
        SearchLog.company_id == current_user.id
    ).order_by(SearchLog.search_date.desc()).all()
    
    unique_recent = []
    seen = set()
    for r in recent:
        term = r[0]
        if term and term not in seen:
            unique_recent.append(term)
            seen.add(term)
        if len(unique_recent) >= 3:
            break
            
    return jsonify(unique_recent)

@api_mobile_bp.route('/products/search', methods=['POST'])
@login_required
def search_products():
    data = request.get_json()
    search_term = data.get('search_term', '').strip()
    if not search_term:
        return jsonify({'error': 'يرجى إدخال كلمة البحث'}), 400

    # Check search limit for non-premium
    if not current_user.is_premium:
        limit_setting = SystemSetting.query.filter_by(setting_key='monthly_search_limit').first()
        limit = int(limit_setting.setting_value) if limit_setting else 30
        now = datetime.utcnow()
        count = SearchLog.query.filter(
            SearchLog.company_id == current_user.id,
            extract('year', SearchLog.search_date) == now.year,
            extract('month', SearchLog.search_date) == now.month
        ).count()
        if count >= limit:
            return jsonify({'error': f'لقد وصلت للحد الأقصى ({limit}) من عمليات البحث لهذا الشهر.'}), 403

    # Log search
    log = SearchLog(company_id=current_user.id, search_term=search_term, search_date=datetime.utcnow())
    db.session.add(log)

    # Get blocked products
    blocked = {bp.product_name.lower() for bp in BlockedProduct.query.all()}
    
    # Get all products and filter
    all_prods = ProductItem.query.all()
    filtered_prods = [p for p in all_prods if p.name.lower() not in blocked]
    names_list = [p.name for p in filtered_prods]

    # Fuzzy search
    matches = process.extractBests(search_term, names_list, scorer=fuzz.partial_ratio, score_cutoff=50)
    
    results = []
    for match, score in matches:
        prods = [p for p in filtered_prods if p.name == match]
        for p in prods:
            results.append({
                'name': p.name,
                'quantity': p.quantity,
                'price': p.price,
                'score': score
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    log.results_count = len(results)
    db.session.commit()

    return jsonify({
        'search_term': search_term,
        'count': len(results),
        'results': results
    })

@api_mobile_bp.route('/products/favorites', methods=['GET'])
@login_required
def get_favorites():
    if session.get('user_type') != 'company':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    favs = FavoriteProduct.query.filter_by(company_id=current_user.id).order_by(FavoriteProduct.last_modified.desc()).all()
    
    result = []
    for f in favs:
        # Latest stock
        stock = ProductStockHistory.query.filter_by(product_name=f.product_name).order_by(ProductStockHistory.record_date.desc(), ProductStockHistory.recorded_at.desc()).first()
        result.append({
            'id': f.id,
            'product_name': f.product_name,
            'current_stock': stock.quantity if stock else (f.quantity or '0'),
            'price': stock.price if stock else (f.price or '0'),
            'notes': f.notes or '',
            'added_at': f.added_at.strftime('%d/%m/%Y') if f.added_at else ''
        })
    
    return jsonify({
        'success': True,
        'is_premium': getattr(current_user, 'is_premium', False),
        'favorites': result
    })

@api_mobile_bp.route('/reports/balance', methods=['GET'])
@login_required
def get_balance_report():
    if session.get('user_type') != 'company':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    if not getattr(current_user, 'is_premium', False):
        return jsonify({'success': False, 'error': 'Premium subscription required'}), 403

    end_date_str = request.args.get('end_date')
    start_date_str = request.args.get('start_date')

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()
    except:
        end_date = date.today()

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else (end_date - timedelta(days=30))
    except:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    report_days_count = (end_date - start_date).days + 1
    if report_days_count <= 0: report_days_count = 1

    favorites = FavoriteProduct.query.filter_by(company_id=current_user.id).all()
    reports_data = []

    for fav in favorites:
        product_name = fav.product_name
        
        # Get history records
        records = ProductStockHistory.query.filter(
            ProductStockHistory.product_name == product_name,
            ProductStockHistory.record_date >= start_date,
            ProductStockHistory.record_date <= end_date
        ).order_by(ProductStockHistory.record_date).all()

        if not records:
            reports_data.append({
                'product_name': product_name,
                'has_data': False,
                'message': 'لا توجد بيانات لهذه الفترة'
            })
            continue

        numeric_records = []
        for rec in records:
            try:
                qty = float(rec.quantity)
                numeric_records.append({'date': rec.record_date.isoformat(), 'quantity': qty})
            except:
                numeric_records.append({'date': rec.record_date.isoformat(), 'quantity': 0.0})

        # Calculate metrics
        inc = 0.0
        dec = 0.0
        for i in range(1, len(numeric_records)):
            diff = numeric_records[i]['quantity'] - numeric_records[i-1]['quantity']
            if diff > 0: inc += diff
            elif diff < 0: dec += abs(diff)

        current_stock = numeric_records[-1]['quantity']
        daily_avg = dec / report_days_count
        
        # Moving avg (last 7)
        recent_chunk = numeric_records[-8:]
        recent_dec = 0.0
        intervals = 0
        for i in range(1, len(recent_chunk)):
            d = recent_chunk[i]['quantity'] - recent_chunk[i-1]['quantity']
            if d < 0: recent_dec += abs(d)
            intervals += 1
        moving_avg = (recent_dec / intervals) if intervals > 0 else 0.0

        # Safety Stock
        daily_changes = []
        for i in range(1, len(recent_chunk)):
            change = recent_chunk[i]['quantity'] - recent_chunk[i-1]['quantity']
            if change < 0: daily_changes.append(abs(change))
        
        safety_stock = 0.0
        if len(daily_changes) >= 2:
            mean = sum(daily_changes) / len(daily_changes)
            var = sum((x - mean) ** 2 for x in daily_changes) / (len(daily_changes) - 1)
            safety_stock = 1.65 * math.sqrt(var) * 7

        base_avg = moving_avg if moving_avg > 0 else daily_avg
        forecast = base_avg * 30
        recommended = max(0, round(forecast - current_stock + safety_stock))

        # Trend text
        trend_val = 0
        if len(numeric_records) >= 7:
            trend_val = numeric_records[-1]['quantity'] - numeric_records[-7]['quantity']
        
        trend_text = "مستقر"
        if trend_val > 5: trend_text = "متصاعد"
        elif trend_val < -5: trend_text = "متناقص"

        reports_data.append({
            'product_name': product_name,
            'has_data': True,
            'start_qty': numeric_records[0]['quantity'],
            'end_qty': current_stock,
            'total_inc': inc,
            'total_dec': dec,
            'daily_avg': round(daily_avg, 1),
            'trend': trend_text,
            'forecast': "استهلاك إضافي" if forecast > current_stock else "مستقر",
            'safety_stock': round(safety_stock, 1),
            'recommended_qty': recommended,
            'history': numeric_records # For sparklines
        })

    return jsonify({
        'success': True,
        'summary': {
            'total_products': len(favorites),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        'reports': reports_data
    })

@api_mobile_bp.route('/products/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    if session.get('user_type') != 'company':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    prod_name = data.get('product_name')
    if not prod_name:
        return jsonify({'success': False, 'message': 'اسم الصنف مطلوب.'}), 400
        
    fav = FavoriteProduct.query.filter_by(company_id=current_user.id, product_name=prod_name).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': False, 'message': 'تم الحذف من الأصناف.'})
    else:
        # Get price and quantity from current stock
        stock = ProductStockHistory.query.filter_by(product_name=prod_name).order_by(ProductStockHistory.record_date.desc()).first()
        new_fav = FavoriteProduct(
            company_id=current_user.id,
            product_name=prod_name,
            price=stock.price if stock else 0,
            quantity=stock.quantity if stock else 0,
            added_at=datetime.utcnow(),
            last_modified=datetime.utcnow()
        )
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': True, 'message': 'تمت الإضافة للأصناف.'})

@api_mobile_bp.route('/products/report_request', methods=['POST'])
@login_required
def request_product_report():
    if session.get('user_type') != 'company':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    prod_name = data.get('product_name')
    if not prod_name:
        return jsonify({'success': False, 'message': 'اسم الصنف مطلوب.'}), 400
        
    # Create admin notification
    notif = Notification(
        title=f'طلب تقرير صنف من {current_user.company_name}',
        message=f'طلب تقرير تفصيلي للصنف: {prod_name}',
        target_type='all',
        created_by=None,
        created_at=datetime.utcnow(),
        notif_type='product_report_request' # Specific type for admin identification
    )
    db.session.add(notif)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إرسال طلب التقرير للإدارة.'})

@api_mobile_bp.route('/products/remember', methods=['POST'])
@login_required
def remember_product():
    data = request.get_json()
    prod_name = data.get('product_name')
    quantity = data.get('quantity', 0)
    
    if not prod_name:
        return jsonify({'success': False, 'message': 'اسم الصنف مطلوب.'}), 400
        
    # Check limit: 1 for free, 5 for premium
    limit = 5 if current_user.is_premium else 1
    existing_count = ProductReminder.query.filter_by(company_id=current_user.id).count()
    
    # If already exists, we update it regardless of limit
    existing = ProductReminder.query.filter_by(company_id=current_user.id, product_name=prod_name).first()
    if existing:
        existing.quantity = quantity
        existing.recorded_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم تحديث الكمية المتذكرة.'})
    
    if existing_count >= limit:
        msg = 'لقد وصلت للحد الأقصى (5 أصناف) في النسخة المميزة.' if current_user.is_premium else 'النسخة المجانية تسمح بتذكر صنف واحد فقط.'
        return jsonify({'success': False, 'message': msg}), 403
        
    reminder = ProductReminder(
        company_id=current_user.id,
        product_name=prod_name,
        quantity=quantity,
        recorded_at=datetime.utcnow()
    )
    db.session.add(reminder)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم حفظ الكمية للتذكر.'})

# --- Appointment Endpoints ---

@api_mobile_bp.route('/appointments', methods=['GET'])
@login_required
def get_appointments():
    appts = Appointment.query.filter_by(company_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
    data = []
    for a in appts:
        data.append({
            'id': a.id,
            'date': a.appointment_date.isoformat(),
            'time': a.appointment_time.strftime('%H:%M'),
            'purpose': a.purpose,
            'product': a.product_item_name,
            'status': a.status,
            'response': a.admin_response,
            'created_at': a.created_at.isoformat()
        })
    return jsonify(data)

@api_mobile_bp.route('/appointments/book', methods=['POST'])
@login_required
def book_appointment():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
        
    try:
        apt_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        apt_time = datetime.strptime(data.get('time'), '%H:%M').time()
        
        # Simple validation
        if apt_date < date.today():
             return jsonify({'success': False, 'message': 'لا يمكن حجز موعد في تاريخ ماضٍ.'}), 400
             
        new_appt = Appointment(
            company_id=current_user.id,
            appointment_date=apt_date,
            appointment_time=apt_time,
            purpose=data.get('purpose'),
            product_item_name=data.get('product'),
            notes=data.get('notes'),
            status='pending'
        )
        db.session.add(new_appt)
        db.session.commit()
        
        # Admin notification
        notif = Notification(
            title=f'طلب موعد جديد من {current_user.company_name} عبر الموبايل',
            message=f'طلب موعد بتاريخ {data.get("date")} الساعة {data.get("time")}.',
            target_type='all',
            created_by=None
        )
        db.session.add(notif)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم إرسال طلب الموعد بنجاح.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Community Endpoints ---

@api_mobile_bp.route('/community/posts', methods=['GET'])
@login_required
def get_posts():
    posts = CommunityPost.query.filter_by(is_active=True).order_by(CommunityPost.created_at.desc()).all()
    data = []
    for p in posts:
        liked = PostLike.query.filter_by(post_id=p.id, company_id=current_user.id).first() is not None
        data.append({
            'id': p.id,
            'company_name': p.company.company_name if not p.is_anonymous else 'مستخدم مجهول',
            'avatar': p.company.avatar if not p.is_anonymous else 'default-male',
            'content': p.content,
            'created_at': p.created_at.isoformat(),
            'likes_count': p.likes_count,
            'comments_count': len(p.comments),
            'liked_by_me': liked,
            'is_pinned': p.is_pinned
        })
    return jsonify(data)

@api_mobile_bp.route('/community/posts/create', methods=['POST'])
@login_required
def create_post():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'المحتوى مطلوب.'}), 400
        
    post = CommunityPost(
        company_id=current_user.id,
        content=content,
        is_anonymous=data.get('is_anonymous', False),
        created_at=datetime.utcnow()
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم نشر المنشور بنجاح.'})

@api_mobile_bp.route('/community/posts/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    post = CommunityPost.query.get_or_404(post_id)
    like = PostLike.query.filter_by(post_id=post_id, company_id=current_user.id).first()
    
    if like:
        db.session.delete(like)
        post.likes_count = max(0, post.likes_count - 1)
        db.session.commit()
        return jsonify({'success': True, 'liked': False, 'likes_count': post.likes_count})
    else:
        new_like = PostLike(post_id=post_id, company_id=current_user.id)
        db.session.add(new_like)
        post.likes_count += 1
        
        # Create notification if not own post
        if post.company_id != current_user.id:
            notif = CommunityNotification(
                company_id=post.company_id,
                post_id=post.id,
                from_company_id=current_user.id,
                message=f'أعجب {current_user.company_name} بمنشورك.',
                notification_type='like'
            )
            db.session.add(notif)
            
        db.session.commit()
        return jsonify({'success': True, 'liked': True, 'likes_count': post.likes_count})

@api_mobile_bp.route('/community/posts/<int:post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    comments = PostComment.query.filter_by(post_id=post_id, is_active=True).order_by(PostComment.created_at.asc()).all()
    data = []
    for c in comments:
        data.append({
            'id': c.id,
            'company_name': c.company.company_name if not c.is_anonymous else 'مستخدم مجهول',
            'avatar': c.company.avatar if not c.is_anonymous else 'default-male',
            'content': c.content,
            'created_at': c.created_at.isoformat()
        })
    return jsonify(data)

@api_mobile_bp.route('/community/posts/<int:post_id>/comments/create', methods=['POST'])
@login_required
def create_comment(post_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'التعليق لا يمكن أن يكون فارغاً.'}), 400
        
    post = CommunityPost.query.get_or_404(post_id)
    comment = PostComment(
        post_id=post_id,
        company_id=current_user.id,
        content=content,
        is_anonymous=data.get('is_anonymous', False),
        created_at=datetime.utcnow()
    )
    db.session.add(comment)
    
    if post.company_id != current_user.id:
        notif = CommunityNotification(
            company_id=post.company_id,
            post_id=post.id,
            comment_id=comment.id,
            from_company_id=current_user.id,
            message=f'علق {current_user.company_name} على منشورك.',
            notification_type='comment'
        )
        db.session.add(notif)
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إضافة التعليق.'})

# --- Private Messaging Endpoints ---

@api_mobile_bp.route('/messages/conversations', methods=['GET'])
@login_required
def get_conversations():
    # Similar to app.py get_conversations but for API
    messages = db.session.query(PrivateMessage).filter(
        or_(PrivateMessage.sender_id == current_user.id, PrivateMessage.receiver_id == current_user.id)
    ).order_by(PrivateMessage.sent_at.desc()).all()
    
    convos = {}
    for m in messages:
        other_id = m.receiver_id if m.sender_id == current_user.id else m.sender_id
        if other_id not in convos:
            other = Company.query.get(other_id)
            if other:
                unread = PrivateMessage.query.filter_by(sender_id=other_id, receiver_id=current_user.id, is_read=False).count()
                convos[other_id] = {
                    'other_company_id': other_id,
                    'company_name': other.company_name,
                    'avatar': other.avatar,
                    'last_message': m.message[:50],
                    'last_message_time': m.sent_at.isoformat() if m.sent_at else None,
                    'unread_count': unread
                }
    
    return jsonify(list(convos.values()))

@api_mobile_bp.route('/messages/conversation/<int:other_id>', methods=['GET'])
@login_required
def get_conversation(other_id):
    messages = db.session.query(PrivateMessage).filter(
        or_(
            and_(PrivateMessage.sender_id == current_user.id, PrivateMessage.receiver_id == other_id),
            and_(PrivateMessage.sender_id == other_id, PrivateMessage.receiver_id == current_user.id)
        )
    ).order_by(PrivateMessage.sent_at.asc()).all()
    
    # Mark as read
    PrivateMessage.query.filter_by(sender_id=other_id, receiver_id=current_user.id, is_read=False).update({'is_read': True, 'read_at': datetime.utcnow()})
    db.session.commit()
    
    data = []
    for m in messages:
        data.append({
            'id': m.id,
            'is_me': m.sender_id == current_user.id,
            'message': m.message,
            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
            'is_read': m.is_read
        })
    return jsonify(data)

@api_mobile_bp.route('/messages/send', methods=['POST'])
@login_required
def send_private_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('message', '').strip()
    
    if not receiver_id or not content:
        return jsonify({'success': False, 'message': 'بيانات غير مكتملة.'}), 400
        
    msg = PrivateMessage(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        subject="رسالة من الموبايل",
        message=content,
        sent_at=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إرسال الرسالة.'})

# --- Notification Endpoints ---

@api_mobile_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifs = Notification.query.filter(
        or_(Notification.target_type == 'all', and_(Notification.target_type == 'specific', Notification.target_id == current_user.id)),
        Notification.is_active == True
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    data = []
    for n in notifs:
        is_read = NotificationRead.query.filter_by(notification_id=n.id, company_id=current_user.id).first() is not None
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'created_at': n.created_at.isoformat(),
            'is_read': is_read
        })
    return jsonify(data)

@api_mobile_bp.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    existing = NotificationRead.query.filter_by(notification_id=notification_id, company_id=current_user.id).first()
    if not existing:
        read = NotificationRead(notification_id=notification_id, company_id=current_user.id)
        db.session.add(read)
        db.session.commit()
    return jsonify({'success': True})

# --- Statuses ---

@api_mobile_bp.route('/statuses', methods=['GET'])
@login_required
def get_statuses():
    now = datetime.utcnow()
    statuses = CompanyStatus.query.filter(
        CompanyStatus.is_active == True,
        CompanyStatus.start_at <= now,
        CompanyStatus.end_at > now
    ).order_by(CompanyStatus.start_at.desc()).all()
    
    data = []
    for s in statuses:
        viewed = CompanyStatusView.query.filter_by(status_id=s.id, viewer_company_id=current_user.id).first() is not None
        data.append({
            'id': s.id,
            'company_name': s.company.company_name,
            'text': s.text,
            'viewed_by_me': viewed,
            'is_mine': s.company_id == current_user.id
        })
    return jsonify(data)

@api_mobile_bp.route('/statuses/create', methods=['POST'])
@login_required
def create_status():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text or len(text) > 200:
        return jsonify({'success': False, 'message': 'النص مطلوب (بحد أقصى 200 حرف).'}), 400
        
    now = datetime.utcnow()
    # Deactivate old status
    CompanyStatus.query.filter_by(company_id=current_user.id, is_active=True).update({'is_active': False})
    
    new_status = CompanyStatus(
        company_id=current_user.id,
        text=text,
        start_at=now,
        end_at=now + timedelta(hours=24),
        is_active=True,
        created_at=now
    )
    db.session.add(new_status)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم نشر الحالة بنجاح.'})

# --- Surveys ---

@api_mobile_bp.route('/surveys', methods=['GET'])
@login_required
def get_surveys():
    surveys = Survey.query.filter_by(is_active=True).all()
    data = []
    for s in surveys:
        status = CompanySurveyStatus.query.filter_by(company_id=current_user.id, survey_id=s.id).first()
        is_completed = status.is_completed if status else False
        data.append({
            'id': s.id,
            'title': s.title,
            'description': s.description,
            'is_mandatory': s.is_mandatory,
            'is_completed': is_completed
        })
    return jsonify(data)

@api_mobile_bp.route('/surveys/<int:survey_id>/questions', methods=['GET'])
@login_required
def get_survey_questions(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    questions = Question.query.filter_by(survey_id=survey_id).order_by(Question.order.asc()).all()
    data = []
    for q in questions:
        data.append({
            'id': q.id,
            'text': q.question_text,
            'type': q.question_type,
            'is_required': q.is_required,
            'options': json.loads(q.options) if q.options else None
        })
    return jsonify({'survey_title': survey.title, 'questions': data})

@api_mobile_bp.route('/surveys/<int:survey_id>/submit', methods=['POST'])
@login_required
def submit_survey(survey_id):
    data = request.get_json()
    answers = data.get('answers', []) # List of {question_id, answer_text, rating_value}
    
    response = SurveyResponse(survey_id=survey_id, company_id=current_user.id)
    db.session.add(response)
    
    for a in answers:
        ans = Answer(
            response=response,
            question_id=a.get('question_id'),
            answer_text=a.get('answer_text'),
            rating_value=a.get('rating_value')
        )
        db.session.add(ans)
    
    # Mark as completed
    status = CompanySurveyStatus.query.filter_by(company_id=current_user.id, survey_id=survey_id).first()
    if not status:
        status = CompanySurveyStatus(company_id=current_user.id, survey_id=survey_id)
        db.session.add(status)
    status.is_completed = True
    status.completed_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إرسال الإجابات بنجاح.'})
