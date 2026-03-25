import sqlite3
import sys
import os

# سكريبت بسيط لتحديث جدول company في قاعدة بيانات SQLite
# الاستخدام:
#   python update_company_columns.py path/to/site.db
# مثال (من مجلد المشروع):
#   python update_company_columns.py instance/site.db

COLUMNS_TO_ADD = [
    ("deactivation_reason", "TEXT"),
    ("deactivated_at", "DATETIME"),
    ("force_password_change", "BOOLEAN DEFAULT 0"),
    ("invite_code_used", "VARCHAR(50)"),
    ("is_premium", "BOOLEAN DEFAULT 0"),
    ("premium_activation_date", "DATETIME"),
    ("premium_end_date", "DATETIME"),
    ("last_community_visit", "DATETIME"),
    ("avatar", "VARCHAR(100) DEFAULT 'male-1'"),
    ("premium_trial_prompted", "BOOLEAN DEFAULT 0"),
    ("premium_trial_active", "BOOLEAN DEFAULT 0"),
    ("premium_trial_start", "DATETIME"),
    ("premium_trial_end", "DATETIME"),
    ("allow_messages_from_companies", "BOOLEAN DEFAULT 1"),
]


def main(db_path: str):
    if not os.path.exists(db_path):
        print(f"❌ ملف قاعدة البيانات غير موجود: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # قراءة أعمدة جدول company الحالية
    cur.execute("PRAGMA table_info(company)")
    existing_cols = {row[1] for row in cur.fetchall()}  # row[1] هو اسم العمود

    print("📋 الأعمدة الحالية في جدول company:")
    print(", ".join(sorted(existing_cols)))

    for col_name, col_def in COLUMNS_TO_ADD:
        if col_name in existing_cols:
            print(f"✅ العمود '{col_name}' موجود بالفعل - لن يتم تعديله")
            continue
        ddl = f"ALTER TABLE company ADD COLUMN {col_name} {col_def}"
        print(f"➕ إضافة العمود '{col_name}' باستخدام: {ddl}")
        cur.execute(ddl)

    conn.commit()
    conn.close()
    print("🎉 تم تحديث جدول company بنجاح (إضافة أي أعمدة ناقصة).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python update_company_columns.py path/to/site.db")
        sys.exit(1)
    main(sys.argv[1])
