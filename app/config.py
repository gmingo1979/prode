# app/config.py
#
# Configuración centralizada de la aplicación.
# Todos los valores sensibles se leen desde variables de entorno (.env).
# Nunca hardcodear credenciales acá.

import os


class Config:

    # ── Flask ────────────────────────────────────────────────
    FLASK_ENV  = os.getenv('FLASK_ENV', 'production')
    SECRET_KEY = os.getenv('SECRET_KEY')  # Sin fallback — la app falla si no está definida

    # ── Base de datos ────────────────────────────────────────
    APP_DIR      = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))

    _db_engine = os.getenv('DB_ENGINE', 'sqlite').lower()

    if _db_engine == 'mysql':
        _host = os.getenv('DB_HOST', 'localhost')
        _port = os.getenv('DB_PORT', '3306')
        _user = os.getenv('DB_USER')
        _pass = os.getenv('DB_PASS', '')
        _name = os.getenv('DB_NAME')
        SQLALCHEMY_DATABASE_URI = (
            f'mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/{_name}?charset=utf8mb4'
        )
    else:
        # SQLite (default)
        _db_filename = os.getenv('DB_PATH', 'prode.db')
        if not os.path.isabs(_db_filename):
            _db_filename = os.path.join(PROJECT_ROOT, _db_filename)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_db_filename}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Aplicación ───────────────────────────────────────────
    NOMBRE_EMPRESA    = os.getenv('NOMBRE_EMPRESA',    'Mi Empresa')
    NOMBRE_EMPRESA_XL = os.getenv('NOMBRE_EMPRESA_XL', 'Mi Empresa S.A.')
    NOMBRE_APLICACION = os.getenv('NOMBRE_APLICACION', 'Prode')
    VERSION           = os.getenv('VERSION',           '1.0.0')
    ANO_COPYRIGHT     = os.getenv('ANO_COPYRIGHT',     '2026')
    BASE_URL          = os.getenv('BASE_URL',          'http://127.0.0.1:5000')

    # ── Imágenes ─────────────────────────────────────────────
    IMG_PRELOADER = os.getenv('IMG_PRELOADER', 'logo.png')
    IMG_LOGO      = os.getenv('IMG_LOGO',      'logo_header.png')

    # ── Uploads ──────────────────────────────────────────────
    UPLOAD_BASE = os.path.join(
        PROJECT_ROOT,
        os.getenv('UPLOAD_BASE', 'app/static/uploads')
    )
    UPLOAD_PROFILE_PICS_FOLDER = os.path.join(
        UPLOAD_BASE, os.getenv('UPLOAD_PROFILE_PICS', 'profile_pics')
    )

    # ── Tamaño máximo de archivos subidos (5 MB) ─────────────
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # ── Email (SMTP) — opcional, para notificaciones ─────────
    MAIL_SERVER         = os.getenv('MAIL_SERVER')
    MAIL_PORT           = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.getenv('MAIL_USE_TLS',  'False').lower() == 'true'
    MAIL_USE_SSL        = os.getenv('MAIL_USE_SSL',  'False').lower() == 'true'
    MAIL_USERNAME       = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD       = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # ── Google OAuth — opcional ───────────────────────────────
    GOOGLE_CLIENT_ID     = os.getenv('GOOGLE_CLIENT_ID',     '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

    # ── MercadoPago — opcional (solo para torneos pagos) ─────
    MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', '')
