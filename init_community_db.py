#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف تحديث قاعدة البيانات لمجتمع البونص
يقوم بإضافة الأعمدة الجديدة المطلوبة لميزة مجتمع البونص
"""

from app import app
from models import db, CommunityPost
from sqlalchemy import text

def update_community_database():
    """تحديث قاعدة البيانات لإضافة الأعمدة الجديدة"""
    with app.app_context():
        try:
            # التحقق من وجود العمود is_pinned
            result = db.session.execute(text("PRAGMA table_info(community_post)")).fetchall()
            columns = [column[1] for column in result]
            
            # إضافة العمود is_pinned إذا لم يكن موجوداً
            if 'is_pinned' not in columns:
                print("إضافة عمود is_pinned...")
                db.session.execute(text("ALTER TABLE community_post ADD COLUMN is_pinned BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("تم إضافة عمود is_pinned بنجاح")
            
            # إضافة العمود pinned_until إذا لم يكن موجوداً
            if 'pinned_until' not in columns:
                print("إضافة عمود pinned_until...")
                db.session.execute(text("ALTER TABLE community_post ADD COLUMN pinned_until DATETIME"))
                db.session.commit()
                print("تم إضافة عمود pinned_until بنجاح")
            
            # إضافة العمود views_count إذا لم يكن موجوداً
            if 'views_count' not in columns:
                print("إضافة عمود views_count...")
                db.session.execute(text("ALTER TABLE community_post ADD COLUMN views_count INTEGER DEFAULT 0"))
                db.session.commit()
                print("تم إضافة عمود views_count بنجاح")
            
            print("تم تحديث قاعدة البيانات بنجاح!")
            
        except Exception as e:
            print(f"خطأ في تحديث قاعدة البيانات: {e}")
            db.session.rollback()

if __name__ == '__main__':
    update_community_database()
