# app/routes/config_visual.py
#
# Rutas para la personalización visual de la aplicación.
#
#   GET  /admin/config-visual   → formulario con selectores de color
#   POST /admin/config-visual   → guarda los colores en BD

import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.db import db
from app.models.config_app import ConfigApp
from app.utils.permisos import requiere_funcion

config_visual_bp = Blueprint('config_visual_bp', __name__)

_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


@config_visual_bp.route('/admin/config-visual', methods=['GET'])
@login_required
@requiere_funcion()
def config_visual():
    config = ConfigApp.obtener()
    return render_template(
        'admin/config_visual.html',
        titulo='Personalización visual',
        config=config,
    )


@config_visual_bp.route('/admin/config-visual', methods=['POST'])
@login_required
@requiere_funcion()
def config_visual_guardar():
    color_primary = request.form.get('color_primary', '').strip()
    color_accent  = request.form.get('color_accent',  '').strip()

    if not _HEX_RE.match(color_primary) or not _HEX_RE.match(color_accent):
        flash('Colores inválidos. Usá el selector para elegirlos.', 'danger')
        return redirect(url_for('config_visual_bp.config_visual'))

    config = ConfigApp.obtener()
    config.color_primary = color_primary
    config.color_accent  = color_accent
    db.session.commit()

    flash('Colores actualizados correctamente.', 'success')
    return redirect(url_for('config_visual_bp.config_visual'))
