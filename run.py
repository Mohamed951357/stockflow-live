# -*- coding: utf-8 -*-
from app import create_app, db
from flask_migrate import Migrate, upgrade

app = create_app()

# Initialize Flask-Migrate
migrate = Migrate()
migrate.init_app(app, db, render_as_batch=True)

# Import models to ensure they are registered with SQLAlchemy
from models import *

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
    app.run(debug=True, port=5001, host='0.0.0.0')
