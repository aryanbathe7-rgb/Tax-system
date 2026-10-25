"""Extension instances live here so any module can import them without
creating circular imports (they are attached to the app in create_app)."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
