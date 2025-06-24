import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tu_clave_secreta')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://lipu_admin:XTHV02bIaM8kXSVuMsZ2Sg7FzZQ5HoQr@dpg-d0qvdpripnbc73ept3m0-a.oregon-postgres.render.com/lipuclimas'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    WTF_CSRF_ENABLED = False