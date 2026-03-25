# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date, time, timedelta
import json
from sqlalchemy import func # NEW: Import func from sqlalchemy
import secrets

db = SQLAlchemy()

class Company(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    force_password_change = db.Column(db.Boolean, default=False)  # إجبار تغيير كلمة السر عند التسجيل القادم
    invite_code_used = db.Column(db.String(50), nullable=True)
    is_premium = db.Column(db.Boolean, default=False)
    # --- العمودين الجديدين الآن معرفين هنا ---
    premium_activation_date = db.Column(db.DateTime, nullable=True)
    premium_end_date = db.Column(db.DateTime, nullable=True)
    # ------------------------------------
    # الأسطر القديمة التي كانت تسبب المشكلة (لو لسه موجودة) سيبها معطلة كما هي:
    # # premium_start_date = db.Column(db.DateTime, nullable=True)
    # # premium_end_date = db.Column(db.DateTime, nullable=True)
    last_community_visit = db.Column(db.DateTime, nullable=True)
    avatar = db.Column(db.String(100), default='default-male')
    dark_mode_enabled = db.Column(db.Boolean, default=False)  # تفعيل الوضع الليلي
    # حظر المراسلات بين الشركات
    messaging_blocked = db.Column(db.Boolean, default=False)
    messaging_block_reason = db.Column(db.Text, nullable=True)
    # تفضيل استقبال رسائل من الشركات الأخرى (يمكن للشركة إيقافه من الإعدادات)
    receive_messages_enabled = db.Column(db.Boolean, default=True)
    # ------------------------------------

    # Method مطلوب لـ Flask-Login لعمل خاصية "تذكرني"
    def get_id(self):
        return str(self.id)

    # إضافة العلاقات الجديدة
    survey_responses = db.relationship('SurveyResponse', backref='company', lazy=True)
    survey_statuses = db.relationship('CompanySurveyStatus', backref='company', lazy=True)

    # ---- خصائص تجربة الاشتراك المميز (لكل مستخدم) ----
    premium_trial_prompted = db.Column(db.Boolean, default=False)
    premium_trial_active = db.Column(db.Boolean, default=False)
    premium_trial_start = db.Column(db.DateTime, nullable=True)
    premium_trial_end = db.Column(db.DateTime, nullable=True)
    # ---- نهاية خصائص تجربة الاشتراك المميز ----
    
    # حقول إلغاء التفعيل
    deactivation_reason = db.Column(db.Text, nullable=True)
    deactivated_at = db.Column(db.DateTime, nullable=True)


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(50), default='editor')
    permissions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Method مطلوب لـ Flask-Login لعمل خاصية "تذكرني"
    def get_id(self):
        return str(self.id)

class ProductFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class ProductItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.String(100), nullable=True)
    price = db.Column(db.String(100), nullable=True)

class ProductStockHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.String(100), nullable=True)
    record_date = db.Column(db.Date, nullable=False, default=date.today)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class PrivateMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    is_deleted_by_sender = db.Column(db.Boolean, default=False)
    is_deleted_by_receiver = db.Column(db.Boolean, default=False)
    
    # العلاقات
    sender = db.relationship('Company', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('Company', foreign_keys=[receiver_id], backref='received_messages')


class PrivateMessageEditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('private_message.id'), nullable=False)
    old_text = db.Column(db.Text, nullable=False)
    new_text = db.Column(db.Text, nullable=False)
    edited_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    edited_by_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    message = db.relationship('PrivateMessage', backref='edit_logs')
    editor = db.relationship('Company')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    product_item_name = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_response = db.Column(db.Text)
    handled_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    collection_amount = db.Column(db.Float, nullable=True)

    company = db.relationship('Company', backref=db.backref('appointments', lazy=True))
    handler = db.relationship('Admin', backref=db.backref('handled_appointments', lazy=True), foreign_keys=[handled_by])

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    creator = db.relationship('Admin', backref=db.backref('sent_notifications', lazy=True), foreign_keys=[created_by])


class NotificationRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('notification_id', 'company_id', name='uq_notification_read'),
    )

class SearchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    search_term = db.Column(db.String(200), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    search_date = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', backref=db.backref('searches', lazy=True))

class FavoriteProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.String(100), nullable=True)
    price = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company', backref=db.backref('favorite_products', lazy=True))

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    image_type = db.Column(db.String(10), nullable=False, default='free')  # 'free', 'premium', or 'all'

    uploader = db.relationship('Admin', backref=db.backref('uploaded_ad_images', lazy=True))


class AdStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_image_id = db.Column(db.Integer, db.ForeignKey('ad_image.id'), nullable=False)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_at = db.Column(db.DateTime, nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    ad_image = db.relationship('AdImage', backref=db.backref('stories', lazy=True))
    created_by_admin = db.relationship('Admin', backref=db.backref('created_ad_stories', lazy=True), foreign_keys=[created_by_admin_id])


class AdStoryView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('ad_story.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    story = db.relationship('AdStory', backref=db.backref('views', lazy=True, cascade='all, delete-orphan'))
    company = db.relationship('Company', backref=db.backref('ad_story_views', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('story_id', 'company_id', name='uq_ad_story_view'),
    )


class AdStoryReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('ad_story.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    story = db.relationship('AdStory', backref=db.backref('reactions', lazy=True, cascade='all, delete-orphan'))
    company = db.relationship('Company', backref=db.backref('ad_story_reactions', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('story_id', 'company_id', name='uq_ad_story_reaction'),
    )


class CompanyStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    company = db.relationship('Company', backref=db.backref('statuses', lazy=True))


class CompanyStatusView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status_id = db.Column(db.Integer, db.ForeignKey('company_status.id'), nullable=False)
    viewer_company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.relationship('CompanyStatus', backref=db.backref('views', lazy=True, cascade='all, delete-orphan'))
    viewer_company = db.relationship('Company', backref=db.backref('company_status_views', lazy=True), foreign_keys=[viewer_company_id])

    __table_args__ = (
        db.UniqueConstraint('status_id', 'viewer_company_id', name='uq_company_status_view'),
    )


class CompanyStatusReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status_id = db.Column(db.Integer, db.ForeignKey('company_status.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.relationship('CompanyStatus', backref=db.backref('reactions', lazy=True, cascade='all, delete-orphan'))
    company = db.relationship('Company', backref=db.backref('company_status_reactions', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('status_id', 'company_id', name='uq_company_status_reaction'),
    )

class CommunityMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_type = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read_by_company = db.Column(db.Boolean, default=False)
    is_read_by_admin = db.Column(db.Boolean, default=False)
    chat_room_id = db.Column(db.String(255), nullable=True)
    attachment_url = db.Column(db.String(255), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    is_system_message = db.Column(db.Boolean, default=False)
    is_to_toby = db.Column(db.Boolean, default=False)

    def to_dict(self):
        # استيراد Company و Admin هنا لتجنب الاستيراد الدائري
        from models import Company, Admin
        
        attachment_url = getattr(self, 'attachment_url', None)

        sender_name = "مجهول"
        # Determine sender_name based on sender_type and sender_id
        if self.sender_type == 'company':
            company = Company.query.get(self.sender_id)
            sender_name = company.company_name if company else f"شركة ID: {self.sender_id}"
        elif self.sender_type == 'admin':
            admin = Admin.query.get(self.sender_id)
            sender_name = admin.full_name or admin.username if admin else f"مدير ID: {self.sender_id}"
        # For system messages, sender_name might be fixed or null
        elif self.is_system_message:
            sender_name = "النظام"


        # Get deleted_by_name if the message is deleted
        deleted_by_name = None
        if self.is_deleted and self.deleted_by:
            deleter_admin = Admin.query.get(self.deleted_by)
            deleted_by_name = deleter_admin.full_name or deleter_admin.username if deleter_admin else f"مدير ID: {self.deleted_by}"

        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'sender_id': self.sender_id,
            'message_text': self.message_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read_by_company': self.is_read_by_company,
            'is_read_by_admin': self.is_read_by_admin,
            'chat_room_id': self.chat_room_id,
            'attachment_url': attachment_url,
            'is_pinned': self.is_pinned,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_at else None,
            'deleted_by': self.deleted_by,
            'is_system_message': self.is_system_message,
            'sender_name': sender_name,
            'deleted_by_name': deleted_by_name, # إضافة اسم المدير الذي حذف الرسالة
            'is_to_toby': self.is_to_toby
        }

# AppDownloadLog Model - MODIFIED
class AppDownloadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    download_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    company = db.relationship('Company', backref=db.backref('app_downloads', lazy=True))

class TobyRequestReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    company = db.relationship('Company', backref=db.backref('toby_requests', lazy=True))

# نموذج استطلاع الرأي
class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_mandatory = db.Column(db.Boolean, default=True)  # هل الاستطلاع إجباري؟
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    questions = db.relationship('Question', backref='survey', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('SurveyResponse', backref='survey', lazy=True)
    company_statuses = db.relationship('CompanySurveyStatus', backref='survey', lazy=True, cascade='all, delete-orphan')
# نموذج لتتبع حالة استكمال الاستطلاع لكل شركة
class CompanySurveyStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # لضمان عدم تكرار السجلات
    __table_args__ = (db.UniqueConstraint('company_id', 'survey_id', name='_company_survey_uc'),)

# نموذج السؤال
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # text, rating, choice
    is_required = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    options = db.Column(db.Text)  # JSON string for multiple choice options

# نموذج إجابة الشركة على الاستطلاع
class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # إجابات الشركة
    answers = db.relationship('Answer', backref='response', lazy=True, cascade='all, delete-orphan')

# نموذج الإجابة على سؤال معين
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('survey_response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text)  # للنصوص والتعليقات
    rating_value = db.Column(db.Integer)  # لقيم التقييم بالنجوم (1-5)
    
    question = db.relationship('Question')  # للوصول السريع لبيانات السؤال

# نموذج منشورات مجتمع البونص
class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    likes_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    is_pinned = db.Column(db.Boolean, default=False)
    pinned_until = db.Column(db.DateTime, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # العلاقات
    company = db.relationship('Company', backref=db.backref('community_posts', lazy=True))
    likes = db.relationship('PostLike', foreign_keys='PostLike.post_id', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('PostComment', foreign_keys='PostComment.post_id', backref='post', lazy=True, cascade='all, delete-orphan')
    views = db.relationship('PostView', foreign_keys='PostView.post_id', backref='post', lazy=True, cascade='all, delete-orphan')

# نموذج إعجابات المنشورات
class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقة مع الشركة
    company = db.relationship('Company', backref=db.backref('post_likes', lazy=True))
    
    # لضمان عدم تكرار الإعجاب من نفس الشركة على نفس المنشور
    __table_args__ = (db.UniqueConstraint('post_id', 'company_id', name='_post_like_uc'),)

# نموذج تعليقات المنشورات
class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # العلاقة مع الشركة
    company = db.relationship('Company', backref=db.backref('post_comments', lazy=True))

# نموذج مشاهدات المنشورات
class PostView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقة مع الشركة
    company = db.relationship('Company', backref=db.backref('post_views', lazy=True))
    
    # لضمان عدم تكرار المشاهدة من نفس الشركة على نفس المنشور
    __table_args__ = (db.UniqueConstraint('post_id', 'company_id', name='_post_view_uc'),)

# نموذج إشعارات المجتمع
class CommunityNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('post_comment.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'comment', 'reply', 'new_post'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    from_company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    
    # العلاقات
    company = db.relationship('Company', foreign_keys=[company_id], backref=db.backref('community_notifications', lazy=True))
    from_company = db.relationship('Company', foreign_keys=[from_company_id])
    post = db.relationship('CommunityPost', backref=db.backref('notifications', lazy=True))
    comment = db.relationship('PostComment', backref=db.backref('notifications', lazy=True))

# نموذج إبلاغات المنشورات
class PostReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # العلاقات
    post = db.relationship('CommunityPost', backref=db.backref('reports', lazy=True))
    reporter = db.relationship('Company', backref=db.backref('post_reports', lazy=True))
    resolver = db.relationship('Admin', backref=db.backref('resolved_reports', lazy=True))
    
    # لضمان عدم تكرار الإبلاغ من نفس الشركة على نفس المنشور
    __table_args__ = (db.UniqueConstraint('post_id', 'reporter_id', name='_post_report_uc'),)

class ProductReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    last_quantity = db.Column(db.String(100), nullable=True)
    last_price = db.Column(db.String(100), nullable=True)
    last_search_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقة مع الشركة
    company = db.relationship('Company', backref='product_reminders')
    
    # فهرس مركب لضمان عدم تكرار الصنف للشركة الواحدة
    __table_args__ = (db.UniqueConstraint('company_id', 'product_name', name='unique_company_product'),)


# نموذج استعادة كلمة السر
class PasswordResetToken(db.Model):
    """نموذج لتخزين رموز استعادة كلمة السر"""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    # العلاقة مع الشركة
    company = db.relationship('Company', backref='reset_tokens')
    
    @staticmethod
    def generate_token():
        """توليد رمز عشوائي آمن"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_reset_token(company_id, expires_in_minutes=30):
        """إنشاء رمز استعادة جديد"""
        token = PasswordResetToken.generate_token()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        reset_token = PasswordResetToken(
            company_id=company_id,
            token=token,
            expires_at=expires_at
        )
        
        db.session.add(reset_token)
        db.session.commit()
        
        return token
    
    def is_valid(self):
        """التحقق من صلاحية الرمز"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_as_used(self):
        """وضع علامة على أن الرمز تم استخدامه"""
        self.used = True
        db.session.commit()

# نموذج الأصناف المحجوبة
class BlockedProduct(db.Model):
    """نموذج لتخزين الأصناف المحجوبة من الظهور للشركات"""
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False, unique=True)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    
    # العلاقة مع المسؤول
    blocker = db.relationship('Admin', backref=db.backref('blocked_products', lazy=True))


class CompanyNameChangeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    old_name = db.Column(db.String(200), nullable=False)
    new_name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    admin_comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)

    company = db.relationship('Company', backref=db.backref('name_change_requests', lazy=True))
    reviewer = db.relationship('Admin', backref=db.backref('reviewed_name_change_requests', lazy=True), foreign_keys=[reviewed_by])

class DbMaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    performed_by = db.Column(db.String(150), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='pending')
    details = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
