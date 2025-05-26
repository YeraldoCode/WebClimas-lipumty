import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:230887@localhost/lipumty_climas'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
    ALLOWED_EXTENSIONS = {'xlsx'}
