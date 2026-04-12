# app/routes/auth.py
#
# Autenticación local (usuario + contraseña) y registro por email.

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.db import db, limiter

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.index'))

    if request.method == 'POST':
        from app.models.usuario import Usuario

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Permitir ingresar con email o username
        usuario = (
            Usuario.query.filter_by(username=username).first()
            or Usuario.query.filter_by(email=username).first()
        )

        if not usuario or usuario.auth_origen != 'Local' or not usuario.check_password(password):
            flash('Usuario/email o contraseña incorrectos.', 'danger')
            return render_template('auth/login.html', titulo='Iniciar sesión')

        if not usuario.puede_ingresar():
            flash('Tu cuenta está bloqueada. Contactá al administrador.', 'warning')
            return render_template('auth/login.html', titulo='Iniciar sesión')

        login_user(usuario, remember=False)
        next_page = request.form.get('next') or request.args.get('next')
        return redirect(next_page or url_for('main_bp.index'))

    return render_template('auth/login.html', titulo='Iniciar sesión')


@auth_bp.route('/registro', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.index'))

    if request.method == 'POST':
        from app.models.usuario import Usuario

        nombre   = request.form.get('nombre',   '').strip()
        apellido = request.form.get('apellido', '').strip()
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')
        confirmar = request.form.get('confirmar_password', '')

        errores = []
        if not nombre:   errores.append('El nombre es obligatorio.')
        if not apellido: errores.append('El apellido es obligatorio.')
        if not email:    errores.append('El email es obligatorio.')
        if len(password) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres.')
        if password != confirmar:
            errores.append('Las contraseñas no coinciden.')

        if not errores:
            if Usuario.query.filter_by(email=email).first():
                errores.append('Ese email ya está registrado.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template('auth/registro.html', titulo='Crear cuenta',
                                   form_data=request.form)

        # Generar username único a partir del email
        username_base = email.split('@')[0].replace('.', '_')
        username = username_base
        sufijo = 1
        while Usuario.query.filter_by(username=username).first():
            username = f'{username_base}{sufijo}'
            sufijo += 1

        from app.models.rol import Rol

        usuario = Usuario(
            nombre      = nombre,
            apellido    = apellido,
            email       = email,
            username    = username,
            estado      = 'Activo',
            auth_origen = 'Local',
        )
        usuario.set_password(password)

        rol_pronosticador = Rol.query.filter_by(nombre='Pronosticador').first()
        if rol_pronosticador:
            usuario.roles = [rol_pronosticador]

        db.session.add(usuario)
        db.session.commit()

        from app.services.prode_mail import enviar_bienvenida
        enviar_bienvenida(usuario)

        login_user(usuario, remember=False)
        flash('¡Cuenta creada! Bienvenido/a al Prode.', 'success')

        # Si había una invitación a grupo pendiente, procesarla
        from flask import session as flask_session
        inv_token = flask_session.get('inv_token')
        if inv_token:
            from app.models.grupo import ProdeGrupoInvitacion
            invitacion = ProdeGrupoInvitacion.query.filter_by(
                token=inv_token, estado='pendiente'
            ).first()
            if invitacion and invitacion.email == email:
                from app.routes.grupos import _procesar_invitacion
                return _procesar_invitacion(invitacion, usuario)

        return redirect(url_for('main_bp.index'))

    return render_template('auth/registro.html', titulo='Crear cuenta', form_data={})


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth_bp.login'))
