import os
from app import app, db, Admin  # أو عدّل حسب ملفك لو مش app

DB_PATH = os.path.join(os.getcwd(), 'db.sqlite3')

def delete_old_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️  تم حذف قاعدة البيانات القديمة.")
    else:
        print("✅ لا توجد قاعدة بيانات قديمة.")

def create_new_db():
    with app.app_context():
        db.create_all()
        print("📦 تم إنشاء قاعدة البيانات والجداول.")

def add_super_admin(username='admin', password='123456'):
    with app.app_context():
        if Admin.query.filter_by(username=username).first():
            print(f"ℹ️ المسؤول '{username}' موجود بالفعل.")
        else:
            new_admin = Admin(
                username=username,
                password=password,
                role='super',
                permissions='all'
            )
            db.session.add(new_admin)
            db.session.commit()
            print(f"✅ تم إضافة مسؤول النظام: {username} / {password}")

if __name__ == '__main__':
    print("🚀 بدء تهيئة المشروع...")
    delete_old_db()
    create_new_db()
    add_super_admin()
    print("🎉 التهيئة تمت بنجاح!")
