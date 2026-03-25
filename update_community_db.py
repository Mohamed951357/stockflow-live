#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تحديث قاعدة البيانات لإضافة ميزات جديدة لمجتمع بونص فارما:
- إضافة حقل is_anonymous للمنشورات والتعليقات
- إنشاء جدول PostView لتتبع المشاهدات
- إنشاء جدول CommunityNotification لإشعارات المجتمع
- تحديث الجداول الموجودة
"""

from app import app
from models import db, CommunityPost, PostComment
from sqlalchemy import text

def update_database():
    """تحديث قاعدة البيانات بالحقول الجديدة"""
    with app.app_context():
        try:
            # إضافة حقل is_anonymous للمنشورات
            try:
                db.session.execute(text("ALTER TABLE community_post ADD COLUMN is_anonymous BOOLEAN DEFAULT FALSE"))
                print("✓ تم إضافة حقل is_anonymous للمنشورات")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"خطأ في إضافة حقل is_anonymous للمنشورات: {e}")

            # إضافة حقل is_anonymous للتعليقات
            try:
                db.session.execute(text("ALTER TABLE post_comment ADD COLUMN is_anonymous BOOLEAN DEFAULT FALSE"))
                print("✓ تم إضافة حقل is_anonymous للتعليقات")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"خطأ في إضافة حقل is_anonymous للتعليقات: {e}")

            # إضافة حقل last_community_visit للشركات
            try:
                db.session.execute(text("ALTER TABLE company ADD COLUMN last_community_visit DATETIME"))
                print("✓ تم إضافة حقل last_community_visit للشركات")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"خطأ في إضافة حقل last_community_visit للشركات: {e}")

            # إضافة حقل avatar للشركات
            try:
                db.session.execute(text("ALTER TABLE company ADD COLUMN avatar VARCHAR(100) DEFAULT 'male-1'"))
                print("✓ تم إضافة حقل avatar للشركات")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"خطأ في إضافة حقل avatar للشركات: {e}")

            # إنشاء جدول PostView
            try:
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS post_view (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER NOT NULL,
                        company_id INTEGER NOT NULL,
                        viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (post_id) REFERENCES community_post (id),
                        FOREIGN KEY (company_id) REFERENCES company (id),
                        UNIQUE(post_id, company_id)
                    )
                """))
                print("✓ تم إنشاء جدول post_view")
            except Exception as e:
                print(f"خطأ في إنشاء جدول post_view: {e}")

            # إنشاء جدول CommunityNotification
            try:
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS community_notification (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL,
                        post_id INTEGER,
                        comment_id INTEGER,
                        message TEXT NOT NULL,
                        notification_type VARCHAR(50) NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        from_company_id INTEGER,
                        FOREIGN KEY (company_id) REFERENCES company (id),
                        FOREIGN KEY (post_id) REFERENCES community_post (id),
                        FOREIGN KEY (comment_id) REFERENCES post_comment (id),
                        FOREIGN KEY (from_company_id) REFERENCES company (id)
                    )
                """))
                print("✓ تم إنشاء جدول community_notification")
            except Exception as e:
                print(f"خطأ في إنشاء جدول community_notification: {e}")

            # حفظ التغييرات
            db.session.commit()
            print("\n✅ تم تحديث قاعدة البيانات بنجاح!")
            print("\nالميزات الجديدة:")
            print("- إمكانية النشر والتعليق مجهول الهوية")
            print("- تتبع دقيق لمشاهدات المنشورات (بدون تكرار)")
            print("- المنشورات المثبتة تظهر في أعلى الصفحة")
            print("- إشعارات المجتمع")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ في تحديث قاعدة البيانات: {e}")

if __name__ == '__main__':
    print("🔄 بدء تحديث قاعدة البيانات...")
    update_database()
