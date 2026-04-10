# app/__init__.py
#
# Factory de la aplicación Flask (patrón Application Factory).

import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

# Cargar .env a nivel de módulo para que Config lea las variables correctas al importarse
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '.env'))

from flask import Flask, render_template, request
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_talisman import Talisman

from app.db import db, limiter
from app.config import Config
from app.oauth import oauth

# ── Extensiones (se inicializan sin app, luego con init_app) ─
login_manager = LoginManager()
mail          = Mail()
migrate       = Migrate()
talisman      = Talisman()

def create_app():
    """Crea y configura la instancia de Flask."""

    base_dir = os.path.abspath(os.path.dirname(__file__))

    # Validar variable crítica
    if not os.getenv('SECRET_KEY'):
        raise RuntimeError(
            "La variable SECRET_KEY no está configurada.\n"
            "Agregála al archivo .env antes de iniciar la app."
        )

    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)
    flask_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    flask_app.secret_key = flask_app.config.get('SECRET_KEY')

    # ── Logging de seguridad (archivo rotativo) ──────────────
    logs_dir = os.path.join(base_dir, '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'security.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s'
    ))
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.setLevel(logging.WARNING)

    # ── Crear carpeta de fotos de perfil ─────────────────────
    os.makedirs(flask_app.config['UPLOAD_PROFILE_PICS_FOLDER'], exist_ok=True)

    # ── Inicializar extensiones ──────────────────────────────
    db.init_app(flask_app)
    mail.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    limiter.init_app(flask_app)

    # ── Google OAuth ─────────────────────────────────────────
    oauth.init_app(flask_app)
    oauth.register(
        name='google',
        client_id=flask_app.config['GOOGLE_CLIENT_ID'],
        client_secret=flask_app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    # ── Flask-Talisman: cabeceras de seguridad HTTP ──────────
    _es_produccion = os.getenv('FLASK_ENV', 'production') == 'production'
    talisman.init_app(
        flask_app,
        force_https=_es_produccion,
        strict_transport_security=_es_produccion,
        strict_transport_security_max_age=31536000,
        content_security_policy=False,
        frame_options='SAMEORIGIN',
        x_content_type_options=True,
        referrer_policy='strict-origin-when-cross-origin',
    )

    # ── Configuración de Flask-Login ─────────────────────────
    login_manager.login_view             = 'auth_bp.login'
    login_manager.login_message          = 'Debés iniciar sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # ── Importar modelos (necesario para que Alembic los detecte)
    import app.models  # noqa: F401

    from app.models.usuario import Usuario
    from app.models.rol     import Rol
    from sqlalchemy.orm     import joinedload

    @login_manager.user_loader
    def load_user(user_id):
        return (
            Usuario.query
            .options(joinedload(Usuario.roles).joinedload(Rol.funciones))
            .get(int(user_id))
        )

    # ── Filtro Jinja2: convierte UTC → hora local (Argentina) ──
    from datetime import datetime, timezone, timedelta

    _TZ_LOCAL = timedelta(hours=-3)

    @flask_app.template_filter('hora_local')
    def hora_local_filter(dt, fmt='%d/%m/%Y %H:%M'):
        """Convierte un datetime UTC a hora local y lo formatea."""
        if dt is None:
            return '—'
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(timezone(_TZ_LOCAL))
        return dt_local.strftime(fmt)

    # ── Variables globales para todos los templates ──────────
    @flask_app.context_processor
    def inject_globals():
        from app.utils.menu import obtener_menu_usuario
        return dict(
            nombre_empresa    = flask_app.config.get('NOMBRE_EMPRESA'),
            nombre_empresa_xl = flask_app.config.get('NOMBRE_EMPRESA_XL'),
            nombre_aplicacion = flask_app.config.get('NOMBRE_APLICACION'),
            version           = flask_app.config.get('VERSION'),
            ano_copyright     = flask_app.config.get('ANO_COPYRIGHT'),
            img_preloader     = flask_app.config.get('IMG_PRELOADER', 'logo.png'),
            img_app           = flask_app.config.get('IMG_LOGO', 'logo_header.png'),
            is_dev            = flask_app.debug,
            menu_sidebar      = obtener_menu_usuario('sidebar'),
            menu_navbar       = obtener_menu_usuario('navbar'),
        )

    @flask_app.before_request
    def registrar_sesion():
        """Crea o actualiza el registro de sesión activa del usuario logueado."""
        from flask import session as flask_session, redirect, url_for
        from flask_login import logout_user
        from app.models.sesion_activa import SesionActiva

        if not current_user.is_authenticated:
            return

        token = flask_session.get('_sesion_token')
        if not token:
            import secrets
            token = secrets.token_hex(32)
            flask_session['_sesion_token'] = token

        ip = (
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.remote_addr
        )

        sesion = SesionActiva.query.filter_by(session_token=token).first()

        if sesion:
            if sesion.invalidada:
                logout_user()
                flask_session.clear()
                return redirect(url_for('auth_bp.login'))

            from datetime import datetime, timezone, timedelta
            ahora = datetime.now(timezone.utc)
            ult   = sesion.ultimo_visto
            if ult.tzinfo is None:
                ult = ult.replace(tzinfo=timezone.utc)
            if (ahora - ult) > timedelta(minutes=1):
                sesion.ultimo_visto = ahora
                sesion.ip           = ip
                db.session.commit()
        else:
            sesion = SesionActiva(
                usuario_id    = current_user.id,
                session_token = token,
                ip            = ip,
                user_agent    = request.user_agent.string[:300],
            )
            db.session.add(sesion)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    # ── Registrar blueprints ─────────────────────────────────
    from app.routes.auth        import auth_bp
    from app.routes.auth_google import auth_google_bp
    from app.routes.main        import main_bp
    from app.routes.usuarios    import usuarios_bp
    from app.routes.roles       import roles_bp
    from app.routes.funciones   import funciones_bp
    from app.routes.prode       import prode_bp
    from app.routes.sesiones    import sesiones_bp
    from app.routes.pwa         import pwa_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(auth_google_bp)
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(usuarios_bp)
    flask_app.register_blueprint(roles_bp)
    flask_app.register_blueprint(funciones_bp)
    flask_app.register_blueprint(prode_bp)
    flask_app.register_blueprint(sesiones_bp)
    flask_app.register_blueprint(pwa_bp)

    # ── Manejadores de error ─────────────────────────────────
    @flask_app.errorhandler(401)
    def unauthorized(e):
        return render_template('errors/401.html', titulo='Sin sesión'), 401

    @flask_app.errorhandler(403)
    def forbidden(e):
        return render_template(
            'errors/403.html',
            titulo='Sin permisos',
            usuario         = current_user.username       if current_user.is_authenticated else None,
            nombre_completo = current_user.nombre_completo if current_user.is_authenticated else None,
            endpoint        = request.endpoint,
        ), 403

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template(
            'errors/404.html',
            titulo   = 'Página no encontrada',
            endpoint = request.path,
        ), 404

    @flask_app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html', titulo='Error del servidor'), 500

    @flask_app.errorhandler(429)
    def too_many_requests(e):
        return render_template('errors/429.html', titulo='Demasiados intentos'), 429

    @flask_app.route('/.well-known/appspecific/com.chrome.devtools.json')
    def chrome_devtools():
        return '', 204

    return flask_app
