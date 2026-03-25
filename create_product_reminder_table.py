#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
سكريبت لإنشاء جدول ProductReminder في قاعدة البيانات
يجب تشغيل هذا السكريبت مرة واحدة فقط لإضافة الجدول
"""

from app import app, db
from models import ProductReminder

def create_product_reminder_table():
    """إنشاء جدول ProductReminder"""
    with app.app_context():
        try:
            # إنشاء الجدول
            db.create_all()
            print("✅ تم إنشاء جدول ProductReminder بنجاح!")
            
            # التحقق من وجود الجدول
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'product_reminder' in tables:
                print("✅ تأكيد: جدول product_reminder موجود في قاعدة البيانات")
                
                # عرض أعمدة الجدول
                columns = inspector.get_columns('product_reminder')
                print("\n📋 أعمدة الجدول:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
                    
                # اختبار إضافة تذكير تجريبي
                print("\n🧪 اختبار إضافة تذكير تجريبي...")
                test_reminder = ProductReminder(
                    company_id=1,  # افتراض وجود شركة برقم 1
                    product_name="منتج تجريبي",
                    last_quantity="10 علب",
                    last_price="100 جنيه"
                )
                
                try:
                    db.session.add(test_reminder)
                    db.session.commit()
                    print("✅ تم إضافة التذكير التجريبي بنجاح!")
                    
                    # حذف التذكير التجريبي
                    db.session.delete(test_reminder)
                    db.session.commit()
                    print("✅ تم حذف التذكير التجريبي بنجاح!")
                    
                except Exception as test_error:
                    print(f"⚠️ خطأ في اختبار التذكير: {str(test_error)}")
                    db.session.rollback()
                    
            else:
                print("❌ خطأ: الجدول غير موجود")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء الجدول: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    return True

if __name__ == '__main__':
    print("🚀 بدء إنشاء جدول ProductReminder...")
    success = create_product_reminder_table()
    
    if success:
        print("\n✅ تم الانتهاء بنجاح!")
        print("📝 يمكنك الآن استخدام ميزة 'تذكر العدد' في صفحة البحث")
        print("📝 الحد الأقصى: 5 تذكيرات لكل شركة")
    else:
        print("\n❌ فشل في إنشاء الجدول")
        print("📝 تحقق من الأخطاء أعلاه وحاول مرة أخرى")
