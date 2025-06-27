import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tu_clave_secreta')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    WTF_CSRF_ENABLED = False