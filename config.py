import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ubah-jadi-random-string-kuat")
    DATABASE = os.path.join(BASE_DIR, "data", "portfolio.db")
    SESSION_COOKIE_SECURE = True   # Wajib True di prod (HTTPS)
    SESSION_COOKIE_HTTPONLY = True