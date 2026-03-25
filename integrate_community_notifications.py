#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
دمج إشعارات التفاعل مع المنشورات في قسم إدارة الإشعارات الرئيسي
"""

def integrate_community_notifications():
    """تعديل route /notifications لإضافة إشعارات التفاعل"""
    
    # قراءة الملف
    with open('views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # البحث عن دالة notifications واستبدالها
    old_function = """    @app.route('/notifications')
    @login_required
    def notifications():
        # احضر كل الإشعارات الموجهة لهذه الشركة أو للجميع
        notifications_for_company = Notification.query.filter(
            db.or_(
                Notification.target_type == 'all',
                db.and_(Notification.target_type == 'specific', Notification.target_id == current_user.id)
            ),
            Notification.is_active == True
        ).order_by(Notification.created_at.desc()).all()

        # علّم هذه الإشعارات كمقروءة لهذه الشركة فقط (تتبع فردي)
        try:
            for notif in notifications_for_company:
                already_read = db.session.query(exists().where(
                    and_(NotificationRead.notification_id == notif.id,
                         NotificationRead.company_id == current_user.id)
                )).scalar()
                if not already_read:
                    db.session.add(NotificationRead(notification_id=notif.id, company_id=current_user.id))
            db.session.commit()
        except Exception:
            db.session.rollback()

        for notif in notifications_for_company:
            if notif.created_at:
                notif.created_at = notif.created_at.replace(tzinfo=pytz.utc).astimezone(CAIRO_TIMEZONE)
            if notif.created_by:
                notif.created_by_user = Admin.query.get(notif.created_by)
            else:
                notif.created_by_user = None

        return render_template('notifications.html', notifications=notifications_for_company)"""
    
    new_function = """    @app.route('/notifications')
    @login_required
    def notifications():
        # احضر كل الإشعارات الموجهة لهذه الشركة أو للجميع
        notifications_for_company = Notification.query.filter(
            db.or_(
                Notification.target_type == 'all',
                db.and_(Notification.target_type == 'specific', Notification.target_id == current_user.id)
            ),
            Notification.is_active == True
        ).order_by(Notification.created_at.desc()).all()

        # احضر إشعارات التفاعل مع المنشورات
        community_notifications = CommunityNotification.query.filter(
            CommunityNotification.company_id == current_user.id
        ).order_by(CommunityNotification.created_at.desc()).all()

        # علّم الإشعارات العادية كمقروءة لهذه الشركة فقط (تتبع فردي)
        try:
            for notif in notifications_for_company:
                already_read = db.session.query(exists().where(
                    and_(NotificationRead.notification_id == notif.id,
                         NotificationRead.company_id == current_user.id)
                )).scalar()
                if not already_read:
                    db.session.add(NotificationRead(notification_id=notif.id, company_id=current_user.id))
            
            # علّم إشعارات التفاعل كمقروءة
            for comm_notif in community_notifications:
                comm_notif.is_read = True
            
            db.session.commit()
        except Exception:
            db.session.rollback()

        # تنسيق التوقيت للإشعارات العادية
        for notif in notifications_for_company:
            if notif.created_at:
                notif.created_at = notif.created_at.replace(tzinfo=pytz.utc).astimezone(CAIRO_TIMEZONE)
            if notif.created_by:
                notif.created_by_user = Admin.query.get(notif.created_by)
            else:
                notif.created_by_user = None

        # تنسيق التوقيت لإشعارات التفاعل
        for comm_notif in community_notifications:
            if comm_notif.created_at:
                comm_notif.created_at = comm_notif.created_at.replace(tzinfo=pytz.utc).astimezone(CAIRO_TIMEZONE)
            # إضافة معلومات الشركة المرسلة
            if comm_notif.from_company_id:
                comm_notif.from_company = Company.query.get(comm_notif.from_company_id)
            else:
                comm_notif.from_company = None

        return render_template('notifications.html', 
                             notifications=notifications_for_company,
                             community_notifications=community_notifications)"""
    
    # استبدال الدالة
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("✅ تم تعديل دالة notifications لتشمل إشعارات التفاعل")
    else:
        print("❌ لم يتم العثور على دالة notifications")
        return False
    
    # كتابة الملف المحدث
    with open('views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تم حفظ الملف بنجاح")
    return True

if __name__ == "__main__":
    print("=== دمج إشعارات التفاعل مع الإشعارات الرئيسية ===")
    if integrate_community_notifications():
        print("تم الدمج بنجاح! إشعارات التفاعل ستظهر الآن في قسم إدارة الإشعارات.")
    else:
        print("فشل في الدمج. تحقق من الملف يدوياً.")
