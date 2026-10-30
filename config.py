import os

class Config:
    # استخدم متغير بيئة أو قيمة افتراضية مؤقتة
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_me')

    # إعدادات قاعدة البيانات MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'medical_ai')
    MYSQL_CURSORCLASS = 'DictCursor'

    # مجلد رفع الصور
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
