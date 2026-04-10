# app/routes/usuarios.py

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import db
from app.forms.usuario_form import UsuarioForm
from app.forms.perfil_form import PerfilForm
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.utils.audit import registrar_accion
from app.utils.imagen_utils import eliminar_foto, procesar_y_guardar_foto

usuarios_bp = Blueprint('usuarios_bp', __name__, url_prefix='/usuarios')

def _upload_folder():
    return current_app.config['UPLOAD_PROFILE_PICS_FOLDER']

# ── Mi Perfil ──────────────────────────────────────────────────────────────
@usuarios_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    form = PerfilForm(obj=current_user)

    if form.validate_on_submit():
        # Verificar username único
        existente = Usuario.query.filter_by(username=form.username.data.strip()).first()
        if existente and existente.id != current_user.id:
            flash(f'El nombre de usuario <strong>{form.username.data}</strong> ya está en uso.', 'danger')
            return render_template('usuarios/perfil.html', form=form)

        # Verificar email único
        if form.email.data:
            existente_email = Usuario.query.filter_by(email=form.email.data.strip()).first()
            if existente_email and existente_email.id != current_user.id:
                flash('El email ya está registrado por otro usuario.', 'danger')
                return render_template('usuarios/perfil.html', form=form)

        current_user.apellido = form.apellido.data.strip()
        current_user.nombre   = form.nombre.data.strip()
        current_user.username = form.username.data.strip().lower()
        current_user.email    = form.email.data.strip() if form.email.data else None

        if form.password_nuevo.data:
            current_user.set_password(form.password_nuevo.data)

        if form.foto.data and form.foto.data.filename:
            try:
                procesar_y_guardar_foto(form.foto.data, current_user.id)
            except ValueError as e:
                flash(str(e), 'warning')

        registrar_accion('editar', 'perfil', current_user.id, 'Actualización de perfil propio')
        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('usuarios_bp.perfil'))

    return render_template('usuarios/perfil.html', form=form)


# ── Eliminar foto de perfil propio ─────────────────────────────────────────
@usuarios_bp.route('/perfil/eliminar-foto', methods=['POST'])
@login_required
def eliminar_foto_propia():
    eliminar_foto(current_user.id)
    flash('Foto de perfil eliminada.', 'success')
    return redirect(url_for('usuarios_bp.perfil'))


# ── Listado ────────────────────────────────────────────────────────────────
@usuarios_bp.route('/')
@login_required
def listado():
    usuarios = Usuario.query.order_by(Usuario.apellido, Usuario.nombre).all()
    return render_template('usuarios/listado.html', titulo='Usuarios', usuarios=usuarios)


# ── Nuevo ──────────────────────────────────────────────────────────────────
@usuarios_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    form = UsuarioForm()
    form.roles.choices = [(r.id, r.nombre) for r in Rol.query.order_by(Rol.nombre).all()]

    if form.validate_on_submit():

        if Usuario.query.filter_by(username=form.username.data.strip()).first():
            flash(f'El usuario <strong>{form.username.data}</strong> ya existe.', 'danger')
            return render_template('usuarios/form.html', titulo='Nuevo usuario', form=form, usuario=None)

        if form.email.data and Usuario.query.filter_by(email=form.email.data.strip()).first():
            flash('El email ya está registrado.', 'danger')
            return render_template('usuarios/form.html', titulo='Nuevo usuario', form=form, usuario=None)

        if form.auth_origen.data == 'Local' and not form.password.data:
            flash('La contraseña es obligatoria para usuarios locales.', 'danger')
            return render_template('usuarios/form.html', titulo='Nuevo usuario', form=form, usuario=None)

        usuario = Usuario(
            apellido    = form.apellido.data.strip(),
            nombre      = form.nombre.data.strip(),
            username    = form.username.data.strip().lower(),
            email       = form.email.data.strip() if form.email.data else None,
            estado      = form.estado.data,
            auth_origen = form.auth_origen.data,
        )

        if form.password.data:
            usuario.set_password(form.password.data)

        if form.roles.data:
            usuario.roles = Rol.query.filter(Rol.id.in_(form.roles.data)).all()

        db.session.add(usuario)
        db.session.flush()

        if form.foto.data and form.foto.data.filename:
            try:
                procesar_y_guardar_foto(form.foto.data, usuario.id)
            except ValueError as e:
                flash(str(e), 'warning')

        registrar_accion('crear', 'usuario', usuario.id,
                         f"Username: {usuario.username} | Roles: {[r.nombre for r in usuario.roles]}")
        db.session.commit()
        flash(f'Usuario <strong>{usuario.nombre_completo}</strong> creado correctamente.', 'success')
        return redirect(url_for('usuarios_bp.listado'))

    return render_template('usuarios/form.html', titulo='Nuevo usuario', form=form, usuario=None)


# ── Editar ─────────────────────────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    usuario = Usuario.query.get_or_404(id)
    form    = UsuarioForm(obj=usuario)
    form.roles.choices = [(r.id, r.nombre) for r in Rol.query.order_by(Rol.nombre).all()]

    if request.method == 'GET':
        form.roles.data = [r.id for r in usuario.roles]

    if form.validate_on_submit():

        existente = Usuario.query.filter_by(username=form.username.data.strip()).first()
        if existente and existente.id != usuario.id:
            flash(f'El usuario <strong>{form.username.data}</strong> ya existe.', 'danger')
            return render_template('usuarios/form.html', titulo='Editar usuario', form=form, usuario=usuario)

        if form.email.data:
            existente_email = Usuario.query.filter_by(email=form.email.data.strip()).first()
            if existente_email and existente_email.id != usuario.id:
                flash('El email ya está registrado por otro usuario.', 'danger')
                return render_template('usuarios/form.html', titulo='Editar usuario', form=form, usuario=usuario)

        usuario.apellido    = form.apellido.data.strip()
        usuario.nombre      = form.nombre.data.strip()
        usuario.username    = form.username.data.strip().lower()
        usuario.email       = form.email.data.strip() if form.email.data else None
        usuario.estado      = form.estado.data
        usuario.auth_origen = form.auth_origen.data

        if form.password.data:
            usuario.set_password(form.password.data)

        usuario.roles = Rol.query.filter(Rol.id.in_(form.roles.data)).all() if form.roles.data else []

        if form.foto.data and form.foto.data.filename:
            try:
                procesar_y_guardar_foto(form.foto.data, usuario.id)
            except ValueError as e:
                flash(str(e), 'warning')

        registrar_accion('editar', 'usuario', usuario.id,
                         f"Username: {usuario.username} | Roles: {[r.nombre for r in usuario.roles]}")
        db.session.commit()
        flash(f'Usuario <strong>{usuario.nombre_completo}</strong> actualizado.', 'success')
        return redirect(url_for('usuarios_bp.listado'))

    return render_template('usuarios/form.html', titulo='Editar usuario', form=form, usuario=usuario)


# ── Eliminar foto ──────────────────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/eliminar-foto', methods=['POST'])
@login_required
def eliminar_foto_perfil(id):
    usuario = Usuario.query.get_or_404(id)
    eliminar_foto(usuario.id)
    flash('Foto de perfil eliminada.', 'success')
    return redirect(url_for('usuarios_bp.editar', id=id))


# ── Cambiar estado ─────────────────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/estado', methods=['POST'])
@login_required
def cambiar_estado(id):
    usuario      = Usuario.query.get_or_404(id)
    nuevo_estado = request.form.get('estado')

    if nuevo_estado not in ('Activo', 'Bloqueado', 'Retirado'):
        flash('Estado inválido.', 'danger')
        return redirect(url_for('usuarios_bp.listado'))

    estado_anterior = usuario.estado
    usuario.estado  = nuevo_estado
    registrar_accion('cambiar_estado', 'usuario', usuario.id,
                     f"Estado: {estado_anterior} → {nuevo_estado}")
    db.session.commit()
    flash(
        f'Usuario <strong>{usuario.nombre_completo}</strong> '
        f'→ <strong>{nuevo_estado}</strong>.',
        'success'
    )
    return redirect(url_for('usuarios_bp.listado'))


# ── Eliminar usuario ───────────────────────────────────────────────────────
@usuarios_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    if id == current_user.id:
        flash('No podés eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('usuarios_bp.listado'))

    usuario = Usuario.query.get_or_404(id)
    try:
        nombre = usuario.nombre_completo
        registrar_accion('eliminar', 'usuario', usuario.id,
                         f"Username: {usuario.username}")
        eliminar_foto(usuario.id)
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario <strong>{nombre}</strong> eliminado.', 'success')
    except Exception:
        db.session.rollback()
        flash(
            'No se puede eliminar este usuario porque tiene registros asociados. '
            'Usá el estado <strong>Retirado</strong> en su lugar.',
            'warning'
        )
    return redirect(url_for('usuarios_bp.listado'))