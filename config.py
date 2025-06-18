import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://lipu_admin:XTHV02bIaM8kXSVuMsZ2Sg7FzZQ5HoQr@dpg-d0qvdpripnbc73ept3m0-a.oregon-postgres.render.com/lipuclimas')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
    ALLOWED_EXTENSIONS = {'xlsx'}
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 5,
        'pool_timeout': 30,
        'pool_recycle': 1800
    }
