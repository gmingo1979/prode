# app/routes/auth_google.py
#
# Autenticación via Google OAuth2.
#
# Flujo:
#   1. Usuario hace click en "Continuar con Google"
#   2. Se redirige a Google para autenticar
#   3. Google redirige a /auth/google/callback con el token
#   4. Se obtiene email + nombre del perfil
#   5a. Si existe usuario con ese google_id → login directo
#   5b. Si existe usuario Local con ese email → error (cuenta ya registrada)
#   5c. Si no existe → crear cuenta activa y loguear
#
# Requiere en .env:
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

from flask import Blueprint, flash, redirect, url_for, session
from flask_login import login_user

from app.db import db
from app.oauth import oauth

auth_google_bp = Blueprint('auth_google_bp', __name__, url_prefix='/auth/google')


@auth_google_bp.route('/login')
def login():
    """Redirige al usuario a la pantalla de login de Google."""
    redirect_uri = url_for('auth_google_bp.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_google_bp.route('/callback')
def callback():
    """Google redirige acá tras autenticar. Crea o recupera el usuario."""
    try:
        token    = oauth.google.authorize_access_token()
        userinfo = token.get('userinfo') or {}
    except Exception as e:
        flash('No se pudo completar el inicio de sesión con Google.', 'danger')
        return redirect(url_for('auth_bp.login'))

    google_id = userinfo.get('sub')
    email     = userinfo.get('email', '').lower().strip()
    nombre    = userinfo.get('given_name') or userinfo.get('name', '').split()[0]
    apellido  = userinfo.get('family_name') or (userinfo.get('name', '').split()[-1]
                 if ' ' in userinfo.get('name', '') else '')
    foto_url  = userinfo.get('picture') or None

    if not google_id or not email:
        flash('Google no devolvió los datos necesarios. Intentá de nuevo.', 'danger')
        return redirect(url_for('auth_bp.login'))

    from app.models.usuario import Usuario

    # ── Caso 1: ya existe cuenta Google con este ID ───────────
    usuario = Usuario.query.filter_by(google_id=google_id).first()
    if usuario:
        if not usuario.puede_ingresar():
            flash('Tu cuenta está bloqueada. Contactá al administrador.', 'warning')
            return redirect(url_for('auth_bp.login'))
        # Actualizar foto si cambió en Google
        if foto_url and usuario.foto_url != foto_url:
            usuario.foto_url = foto_url
            db.session.commit()
        login_user(usuario, remember=False)
        session['auth_provider'] = 'google'
        return redirect(url_for('main_bp.index'))

    # ── Caso 2: mismo email pero cuenta local ─────────────────
    existente = Usuario.query.filter_by(email=email).first()
    if existente and existente.auth_origen == 'Local':
        flash(
            f'El email <strong>{email}</strong> ya está registrado con usuario y contraseña. '
            'Iniciá sesión de forma local.',
            'warning'
        )
        return redirect(url_for('auth_bp.login'))

    # ── Caso 3: vincular si mismo email + Google ──────────────
    if existente and existente.auth_origen == 'Google':
        existente.google_id = google_id
        if foto_url and existente.foto_url != foto_url:
            existente.foto_url = foto_url
        db.session.commit()
        login_user(existente, remember=False)
        session['auth_provider'] = 'google'
        return redirect(url_for('main_bp.index'))

    # ── Caso 4: cuenta nueva ──────────────────────────────────
    from app.models.rol import Rol

    username_base = email.split('@')[0].lower().replace('.', '_')
    username = username_base
    sufijo = 1
    while Usuario.query.filter_by(username=username).first():
        username = f'{username_base}{sufijo}'
        sufijo += 1

    nuevo = Usuario(
        nombre      = nombre    or 'Usuario',
        apellido    = apellido  or '',
        username    = username,
        email       = email,
        estado      = 'Activo',
        auth_origen = 'Google',
        google_id   = google_id,
        foto_url    = foto_url,
    )

    rol_pronosticador = Rol.query.filter_by(nombre='Pronosticador').first()
    if rol_pronosticador:
        nuevo.roles = [rol_pronosticador]

    db.session.add(nuevo)
    db.session.commit()

    login_user(nuevo, remember=False)
    session['auth_provider'] = 'google'
    flash('¡Cuenta creada! Bienvenido/a.', 'success')
    return redirect(url_for('main_bp.index'))
