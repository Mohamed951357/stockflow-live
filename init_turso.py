import os
from app import create_app
from models import db, Admin, SystemSetting

def init_turso():
    import libsql_experimental as libsql
    url = "libsql://stockflow-final-stockflow.aws-us-east-2.turso.io"
    auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NzQ0NjMxMTcsImlkIjoiMDE5ZDI2M2UtMjkwMS03ZWI1LTk5MzQtMjdjZTgyMTA3YzU3IiwicmlkIjoiYzVmNzc2YTktZjczOS00MzEzLWFjZGBeMzY1MmVhMmI2NDBlIn0.TJmug5RtfC_9LFxuPXRanx22oUmdgOwnH2oJGdLeX3imFIJITzXJM6Cry6svWupNOj4qSjzPnAK-nDK5CWJIDQ"
    
    try:
        conn = libsql.connect("stockflow.db", sync_url=url, auth_token=auth_token)
        conn.sync()
        print("Successfully connected and synced with Turso!")
    except Exception as e:
        print(f"Failed to connect to Turso: {e}")
        return

    app = create_app()
    with app.app_context():
        print("Creating all tables on Turso...")
        db.create_all()
        
        print("Checking for super admin...")
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin',
                password='admin_password_2026', # You should change this later
                role='super',
                permissions='["all"]'
            )
            db.session.add(admin)
            print("Super admin created.")
        
        print("Checking for essential settings...")
        if not SystemSetting.query.filter_by(setting_key='current_logo').first():
            logo = SystemSetting(setting_key='current_logo', setting_value='')
            db.session.add(logo)
            print("Default logo setting created.")
            
        db.session.commit()
        print("Initialization complete!")

if __name__ == "__main__":
    init_turso()
