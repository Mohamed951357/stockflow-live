import sqlite3
import os
from datetime import datetime, timedelta

# إعدادات
OLD_DB = 'db.sqlite3'
NEW_DB = 'db_new.sqlite3'
DAYS_TO_KEEP = 30
cutoff_date = (datetime.utcnow() - timedelta(days=DAYS_TO_KEEP)).strftime('%Y-%m-%d %H:%M:%S')

def get_table_names(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def copy_table(table_name, old_conn, new_conn):
    print(f"📦 جاري معالجة الجدول: {table_name}...")
    
    # قراءة هيكل الجدول
    cursor = old_conn.cursor()
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    create_statement = cursor.fetchone()[0]
    
    # إنشاء الجدول في القاعدة الجديدة
    new_conn.execute(create_statement)
    
    # تحديد استعلام النسخ بناءً على نوع الجدول
    # الجداول التي يجب تنظيفها (الاحتفاظ بآخر 30 يوم فقط)
    tables_to_clean = [
        'search_log', 
        'notification', 
        'notification_read', 
        'community_notification',
        'toby_request_report',
        'app_download_log',
        'ad_story_view',
        'company_status_view'
    ]
    
    # الجداول الهامة جداً (الاحتفاظ بكل شيء)
    # Company, Admin, ProductItem, Subscription related tables...
    
    if table_name in tables_to_clean:
        # محاولة العثور على عمود التاريخ المناسب
        date_columns = ['created_at', 'search_date', 'download_time', 'timestamp', 'viewed_at', 'read_at']
        date_col = None
        
        # فحص أعمدة الجدول
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        
        for col in date_columns:
            if col in columns:
                date_col = col
                break
        
        if date_col:
            print(f"   🧹 تنظيف {table_name}: الاحتفاظ بالبيانات بعد {cutoff_date}")
            query = f"SELECT * FROM {table_name} WHERE {date_col} >= ?"
            params = (cutoff_date,)
        else:
            print(f"   ⚠️ لم يتم العثور على عمود تاريخ في {table_name}، سيتم نسخ الكل.")
            query = f"SELECT * FROM {table_name}"
            params = ()
            
    else:
        # نسخ كامل للجداول الأخرى (مثل المستخدمين والاشتراكات)
        print(f"   ✅ نسخ كامل لـ {table_name}")
        query = f"SELECT * FROM {table_name}"
        params = ()

    # تنفيذ النسخ
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if rows:
        placeholders = ','.join(['?'] * len(rows[0]))
        new_conn.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
        new_conn.commit()
    
    print(f"   ✨ تم نسخ {len(rows)} سجل.")

def main():
    if not os.path.exists(OLD_DB):
        print(f"❌ ملف قاعدة البيانات {OLD_DB} غير موجود!")
        return

    # حذف القاعدة الجديدة المؤقتة إذا كانت موجودة
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)

    try:
        old_conn = sqlite3.connect(OLD_DB)
        new_conn = sqlite3.connect(NEW_DB)
        
        # تسريع العملية
        new_conn.execute("PRAGMA synchronous = OFF")
        new_conn.execute("PRAGMA journal_mode = MEMORY")

        tables = get_table_names(old_conn)
        
        # استثناء جدول sqlite_sequence (يتم التعامل معه تلقائياً)
        if 'sqlite_sequence' in tables:
            tables.remove('sqlite_sequence')

        for table in tables:
            copy_table(table, old_conn, new_conn)

        old_conn.close()
        new_conn.close()
        
        print("\n🔄 استبدال قاعدة البيانات القديمة بالجديدة...")
        os.remove(OLD_DB)
        os.rename(NEW_DB, OLD_DB)
        print("🎉 تمت العملية بنجاح! تم تقليص حجم قاعدة البيانات.")
        
    except Exception as e:
        print(f"\n❌ حدث خطأ: {e}")
        if os.path.exists(NEW_DB):
            os.remove(NEW_DB)

if __name__ == '__main__':
    main()
