# -*- coding: utf-8 -*-
# app/routes/sesiones.py
#
# Módulo: Sesiones Activas
# Solo visible para el rol Administrador.
#
# Rutas:
#   GET  /sesiones/          → listado de sesiones activas/recientes
#   POST /sesiones/<id>/cerrar → fuerza cierre de sesión de un usuario

from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.db import db
from app.models.sesion_activa import SesionActiva, TIMEOUT_MINUTOS
from app.utils.permisos import requiere_funcion

sesiones_bp = Blueprint('sesiones', __name__, url_prefix='/sesiones')


@sesiones_bp.route('/')
@login_required
@requiere_funcion()
def listado():
    """Panel de sesiones activas — solo Administrador."""
    # Limpieza de registros muy viejos antes de mostrar
    SesionActiva.limpiar_viejas()

    sesiones = (
        SesionActiva.query
        .filter_by(invalidada=False)
        .order_by(SesionActiva.ultimo_visto.desc())
        .all()
    )

    activas   = [s for s in sesiones if s.activa]
    inactivas = [s for s in sesiones if not s.activa]

    return render_template(
        'sesiones/listado.html',
        titulo        = 'Sesiones activas',
        activas       = activas,
        inactivas     = inactivas,
        timeout_min   = TIMEOUT_MINUTOS,
        now           = datetime.now(timezone.utc),
        mi_token      = current_user.sesiones
                        .filter_by(invalidada=False)
                        .order_by(SesionActiva.ultimo_visto.desc())
                        .first(),
    )


@sesiones_bp.route('/<int:id>/cerrar', methods=['POST'])
@login_required
@requiere_funcion()
def cerrar(id):
    """Invalida una sesión. El usuario será deslogueado en su próximo request."""
    sesion = SesionActiva.query.get_or_404(id)

    # No puede cerrarse a sí mismo desde acá (tiene su propio logout)
    if sesion.usuario_id == current_user.id:
        return jsonify({'ok': False, 'msg': 'No podés cerrar tu propia sesión desde acá.'}), 400

    sesion.invalidada = True
    db.session.commit()
    return jsonify({'ok': True})