# app/routes/roles.py
#
# ABM de roles del sistema.
# Un rol agrupa funciones y se asigna a usuarios.
#
# Rutas:
#   GET  /roles/             → listado con funciones y usuarios por rol
#   GET  /roles/nuevo        → formulario nuevo rol
#   POST /roles/nuevo        → crear rol
#   GET  /roles/<id>/editar  → formulario editar + asignar funciones
#   POST /roles/<id>/editar  → guardar cambios
#   POST /roles/<id>/eliminar→ eliminar (solo si no tiene usuarios)

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.db import db
from app.forms.rol_form import RolForm
from app.models.funcion import Funcion
from app.models.rol import Rol
from app.utils.audit import registrar_accion

roles_bp = Blueprint('roles_bp', __name__, url_prefix='/roles')


@roles_bp.route('/')
@login_required
def listado():
    """Lista todos los roles con sus funciones y usuarios asignados."""
    roles = Rol.query.order_by(Rol.nombre).all()

    # Pre-agrupar funciones por categoría para cada rol en Python
    # evita el error de comparar None vs str en Jinja2 | sort
    funciones_por_rol = {}
    for rol in roles:
        agrupadas = {}
        for f in sorted(rol.funciones, key=lambda x: x.nombre):
            cat = f.categoria or 'Sin categoría'
            agrupadas.setdefault(cat, []).append(f)
        funciones_por_rol[rol.id] = dict(sorted(agrupadas.items()))

    return render_template(
        'roles/listado.html',
        titulo='Roles y permisos',
        roles=roles,
        funciones_por_rol=funciones_por_rol
    )


@roles_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    """Formulario para crear un nuevo rol."""
    form = RolForm()

    # Funciones disponibles agrupadas por categoría para los checkboxes
    funciones_agrupadas = _funciones_agrupadas()

    if form.validate_on_submit():

        if Rol.query.filter_by(nombre=form.nombre.data.strip()).first():
            flash(f'Ya existe un rol llamado <strong>{form.nombre.data}</strong>.', 'danger')
            return render_template('roles/form.html',
                titulo='Nuevo rol', form=form, rol=None,
                funciones_agrupadas=funciones_agrupadas, ids_asignados=[])

        rol = Rol(
            nombre      = form.nombre.data.strip(),
            descripcion = form.descripcion.data.strip() if form.descripcion.data else None,
        )

        # Asignar funciones seleccionadas
        ids_seleccionados = request.form.getlist('funciones')
        if ids_seleccionados:
            rol.funciones = Funcion.query.filter(
                Funcion.id.in_([int(i) for i in ids_seleccionados])
            ).all()

        db.session.add(rol)
        db.session.flush()
        registrar_accion('crear', 'rol', rol.id,
                         f"Nombre: {rol.nombre} | Funciones: {[f.nombre for f in rol.funciones]}")
        db.session.commit()

        flash(f'Rol <strong>{rol.nombre}</strong> creado correctamente.', 'success')
        return redirect(url_for('roles_bp.listado'))

    return render_template('roles/form.html',
        titulo='Nuevo rol', form=form, rol=None,
        funciones_agrupadas=funciones_agrupadas, ids_asignados=[])


@roles_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Formulario para editar un rol y sus funciones asignadas."""
    rol  = Rol.query.get_or_404(id)
    form = RolForm(obj=rol)

    funciones_agrupadas = _funciones_agrupadas()
    ids_asignados = [f.id for f in rol.funciones]

    if form.validate_on_submit():

        existente = Rol.query.filter_by(nombre=form.nombre.data.strip()).first()
        if existente and existente.id != rol.id:
            flash(f'Ya existe un rol llamado <strong>{form.nombre.data}</strong>.', 'danger')
            return render_template('roles/form.html',
                titulo='Editar rol', form=form, rol=rol,
                funciones_agrupadas=funciones_agrupadas,
                ids_asignados=ids_asignados)

        rol.nombre      = form.nombre.data.strip()
        rol.descripcion = form.descripcion.data.strip() if form.descripcion.data else None

        # Actualizar funciones — reemplazar lista completa
        ids_seleccionados = request.form.getlist('funciones')
        rol.funciones = Funcion.query.filter(
            Funcion.id.in_([int(i) for i in ids_seleccionados])
        ).all() if ids_seleccionados else []

        registrar_accion('editar', 'rol', rol.id,
                         f"Nombre: {rol.nombre} | Funciones: {[f.nombre for f in rol.funciones]}")
        db.session.commit()
        flash(f'Rol <strong>{rol.nombre}</strong> actualizado.', 'success')
        return redirect(url_for('roles_bp.listado'))

    return render_template('roles/form.html',
        titulo='Editar rol', form=form, rol=rol,
        funciones_agrupadas=funciones_agrupadas,
        ids_asignados=ids_asignados)


@roles_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    """
    Elimina un rol. No se puede eliminar si tiene usuarios asignados
    para no dejar usuarios sin acceso accidentalmente.
    """
    rol = Rol.query.get_or_404(id)

    if rol.usuarios:
        flash(
            f'No se puede eliminar <strong>{rol.nombre}</strong> porque tiene '
            f'<strong>{len(rol.usuarios)}</strong> usuario(s) asignado(s). '
            f'Reasigná los usuarios primero.',
            'warning'
        )
        return redirect(url_for('roles_bp.listado'))

    try:
        nombre = rol.nombre
        registrar_accion('eliminar', 'rol', rol.id, f"Nombre: {nombre}")
        db.session.delete(rol)
        db.session.commit()
        flash(f'Rol <strong>{nombre}</strong> eliminado.', 'success')
    except Exception:
        db.session.rollback()
        flash('No se pudo eliminar el rol.', 'danger')

    return redirect(url_for('roles_bp.listado'))


# ── Helpers ────────────────────────────────────────────────────────────────

def _funciones_agrupadas() -> dict:
    """
    Devuelve todas las funciones agrupadas por categoría.
    Se usa en el formulario de roles para mostrar los checkboxes agrupados.
    """
    funciones = Funcion.query.order_by(Funcion.categoria, Funcion.nombre).all()
    agrupadas = {}
    for f in funciones:
        cat = f.categoria or 'Sin categoría'
        agrupadas.setdefault(cat, []).append(f)
    return agrupadas
