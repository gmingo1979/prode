# app/routes/funciones.py
#
# ABM de funciones del sistema.
# Las funciones son los permisos/ítems de menú que se asignan a los roles.
#
# Rutas:
#   GET  /funciones/             → listado agrupado por categoría
#   GET  /funciones/nueva        → formulario nueva función
#   POST /funciones/nueva        → crear función
#   GET  /funciones/<id>/editar  → formulario editar función
#   POST /funciones/<id>/editar  → guardar cambios
#   POST /funciones/<id>/eliminar→ eliminar (solo si no tiene roles asignados)

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.db import db
from app.utils.permisos import requiere_funcion
from app.forms.funcion_form import FuncionForm
from app.models.funcion import Funcion

funciones_bp = Blueprint('funciones_bp', __name__, url_prefix='/funciones')


@funciones_bp.route('/')
@login_required
@requiere_funcion()
def listado():
    """Lista todas las funciones agrupadas por categoría."""
    funciones = Funcion.query.order_by(Funcion.categoria, Funcion.nombre).all()

    return render_template(
        'funciones/listado.html',
        titulo='Funciones del sistema',
        funciones=funciones,
        total=len(funciones)
    )


@funciones_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def nueva():
    """Formulario para crear una nueva función."""
    form = FuncionForm()

    if form.validate_on_submit():

        # Validar endpoint único
        if Funcion.query.filter_by(endpoint=form.endpoint.data.strip()).first():
            flash(f'El endpoint <strong>{form.endpoint.data}</strong> ya existe.', 'danger')
            return render_template('funciones/form.html', titulo='Nueva función', form=form, funcion=None)

        # Validar nombre único
        if Funcion.query.filter_by(nombre=form.nombre.data.strip()).first():
            flash(f'Ya existe una función llamada <strong>{form.nombre.data}</strong>.', 'danger')
            return render_template('funciones/form.html', titulo='Nueva función', form=form, funcion=None)

        funcion = Funcion(
            nombre         = form.nombre.data.strip(),
            endpoint       = form.endpoint.data.strip(),
            descripcion    = form.descripcion.data.strip() if form.descripcion.data else None,
            icono          = form.icono.data.strip() if form.icono.data else None,
            categoria      = form.categoria.data.strip() if form.categoria.data else None,
            es_menu        = form.es_menu.data,
            ubicacion_menu = form.ubicacion_menu.data,
        )

        db.session.add(funcion)
        db.session.commit()

        flash(f'Función <strong>{funcion.nombre}</strong> creada correctamente.', 'success')
        return redirect(url_for('funciones_bp.listado'))

    return render_template('funciones/form.html', titulo='Nueva función', form=form, funcion=None)


@funciones_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def editar(id):
    """Formulario para editar una función existente."""
    funcion = Funcion.query.get_or_404(id)
    form    = FuncionForm(obj=funcion)

    if form.validate_on_submit():

        # Validar endpoint único (excluir el propio)
        existente = Funcion.query.filter_by(endpoint=form.endpoint.data.strip()).first()
        if existente and existente.id != funcion.id:
            flash(f'El endpoint <strong>{form.endpoint.data}</strong> ya está en uso.', 'danger')
            return render_template('funciones/form.html', titulo='Editar función', form=form, funcion=funcion)

        # Validar nombre único (excluir el propio)
        existente_nombre = Funcion.query.filter_by(nombre=form.nombre.data.strip()).first()
        if existente_nombre and existente_nombre.id != funcion.id:
            flash(f'Ya existe una función llamada <strong>{form.nombre.data}</strong>.', 'danger')
            return render_template('funciones/form.html', titulo='Editar función', form=form, funcion=funcion)

        funcion.nombre         = form.nombre.data.strip()
        funcion.endpoint       = form.endpoint.data.strip()
        funcion.descripcion    = form.descripcion.data.strip() if form.descripcion.data else None
        funcion.icono          = form.icono.data.strip() if form.icono.data else None
        funcion.categoria      = form.categoria.data.strip() if form.categoria.data else None
        funcion.es_menu        = form.es_menu.data
        funcion.ubicacion_menu = form.ubicacion_menu.data

        db.session.commit()
        flash(f'Función <strong>{funcion.nombre}</strong> actualizada.', 'success')
        return redirect(url_for('funciones_bp.listado'))

    return render_template('funciones/form.html', titulo='Editar función', form=form, funcion=funcion)


@funciones_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
@requiere_funcion()
def eliminar(id):
    """
    Elimina una función. Si está asignada a algún rol, no se puede eliminar
    para no romper los permisos de usuarios activos.
    """
    funcion = Funcion.query.get_or_404(id)

    if funcion.roles:
        roles_nombres = ', '.join(r.nombre for r in funcion.roles)
        flash(
            f'No se puede eliminar <strong>{funcion.nombre}</strong> porque está asignada '
            f'a los roles: <strong>{roles_nombres}</strong>. '
            f'Quitala de esos roles primero.',
            'warning'
        )
        return redirect(url_for('funciones_bp.listado'))

    try:
        nombre = funcion.nombre
        db.session.delete(funcion)
        db.session.commit()
        flash(f'Función <strong>{nombre}</strong> eliminada.', 'success')
    except Exception:
        db.session.rollback()
        flash('No se pudo eliminar la función.', 'danger')

    return redirect(url_for('funciones_bp.listado'))
