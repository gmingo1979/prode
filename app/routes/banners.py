# app/routes/banners.py
#
# Administración de banners publicitarios y tracking de clicks.
#
#   GET/POST /admin/banners           → lista y acciones
#   GET/POST /admin/banners/nuevo     → crear banner
#   GET/POST /admin/banners/<id>      → editar banner
#   POST     /admin/banners/<id>/eliminar → eliminar
#   POST     /admin/banners/<id>/toggle   → activar/desactivar
#   GET      /b/<id>                  → registrar click y redirigir

import os

from flask import (Blueprint, abort, current_app, flash,
                   redirect, render_template, request, url_for)
from flask_login import login_required
from PIL import Image

from app.db import db
from app.models.banner import Banner, POSICIONES, POSICION_INFO
from app.utils.permisos import requiere_funcion

banners_bp = Blueprint('banners_bp', __name__)

_UPLOAD_SUBDIR  = 'uploads/banners'
_ALLOWED_EXT    = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
_MAX_WIDTH      = 1400   # px — se redimensiona si supera este ancho


def _banners_folder():
    return os.path.join(current_app.static_folder, _UPLOAD_SUBDIR)


def _guardar_imagen(file_storage, banner_id: int) -> str:
    """
    Guarda la imagen del banner redimensionándola a max _MAX_WIDTH px de ancho.
    Devuelve la ruta relativa a static/ para guardar en DB.
    """
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in _ALLOWED_EXT:
        raise ValueError('Formato no permitido. Usá JPG, PNG, WEBP o GIF.')

    folder = _banners_folder()
    os.makedirs(folder, exist_ok=True)

    filename = f'banner_{banner_id}.jpg'
    dest     = os.path.join(folder, filename)

    img = Image.open(file_storage)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    elif img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg

    if img.width > _MAX_WIDTH:
        ratio  = _MAX_WIDTH / img.width
        height = int(img.height * ratio)
        img = img.resize((_MAX_WIDTH, height), Image.LANCZOS)

    img.save(dest, 'JPEG', quality=85, optimize=True)
    return f'{_UPLOAD_SUBDIR}/{filename}'


def _eliminar_imagen(banner_id: int):
    path = os.path.join(_banners_folder(), f'banner_{banner_id}.jpg')
    if os.path.exists(path):
        os.remove(path)


# ── Admin: lista ─────────────────────────────────────────────────────────────

@banners_bp.route('/admin/banners')
@login_required
@requiere_funcion()
def admin_banners():
    banners = Banner.query.order_by(Banner.posicion, Banner.orden, Banner.id).all()
    return render_template(
        'prode/admin/banners/lista.html',
        titulo   = 'Admin — Banners',
        banners  = banners,
        posiciones = POSICIONES,
    )


# ── Admin: crear ─────────────────────────────────────────────────────────────

@banners_bp.route('/admin/banners/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_banner_nuevo():
    if request.method == 'POST':
        banner = Banner(
            titulo      = request.form.get('titulo', '').strip(),
            url_destino = request.form.get('url_destino', '').strip() or None,
            posicion    = request.form.get('posicion', 'header'),
            activo      = 'activo' in request.form,
            fecha_desde = _parse_date(request.form.get('fecha_desde')),
            fecha_hasta = _parse_date(request.form.get('fecha_hasta')),
            orden       = int(request.form.get('orden') or 0),
        )
        if not banner.titulo:
            flash('El título es obligatorio.', 'danger')
            return render_template('prode/admin/banners/form.html',
                                   titulo='Nuevo banner', banner=banner,
                                   posiciones=POSICIONES, posicion_info=POSICION_INFO)

        db.session.add(banner)
        db.session.flush()  # obtener banner.id antes de guardar imagen

        archivo = request.files.get('imagen')
        if archivo and archivo.filename:
            try:
                banner.imagen_path = _guardar_imagen(archivo, banner.id)
            except Exception as e:
                flash(str(e), 'danger')
                db.session.rollback()
                return render_template('prode/admin/banners/form.html',
                                       titulo='Nuevo banner', banner=banner,
                                       posiciones=POSICIONES, posicion_info=POSICION_INFO)

        db.session.commit()
        flash(f'Banner "{banner.titulo}" creado.', 'success')
        return redirect(url_for('banners_bp.admin_banners'))

    banner = Banner(activo=True, orden=0, posicion='header')
    return render_template('prode/admin/banners/form.html',
                           titulo='Nuevo banner', banner=banner,
                           posiciones=POSICIONES,
                           posicion_info=POSICION_INFO)


# ── Admin: editar ─────────────────────────────────────────────────────────────

@banners_bp.route('/admin/banners/<int:banner_id>', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_banner_editar(banner_id):
    banner = Banner.query.get_or_404(banner_id)

    if request.method == 'POST':
        banner.titulo      = request.form.get('titulo', '').strip()
        banner.url_destino = request.form.get('url_destino', '').strip() or None
        banner.posicion    = request.form.get('posicion', 'header')
        banner.activo      = 'activo' in request.form
        banner.fecha_desde = _parse_date(request.form.get('fecha_desde'))
        banner.fecha_hasta = _parse_date(request.form.get('fecha_hasta'))
        banner.orden       = int(request.form.get('orden') or 0)

        if not banner.titulo:
            flash('El título es obligatorio.', 'danger')
            return render_template('prode/admin/banners/form.html',
                                   titulo='Editar banner', banner=banner,
                                   posiciones=POSICIONES, posicion_info=POSICION_INFO)

        archivo = request.files.get('imagen')
        if archivo and archivo.filename:
            try:
                banner.imagen_path = _guardar_imagen(archivo, banner.id)
            except Exception as e:
                flash(str(e), 'danger')
                return render_template('prode/admin/banners/form.html',
                                       titulo='Editar banner', banner=banner,
                                       posiciones=POSICIONES, posicion_info=POSICION_INFO)

        db.session.commit()
        flash(f'Banner "{banner.titulo}" actualizado.', 'success')
        return redirect(url_for('banners_bp.admin_banners'))

    return render_template('prode/admin/banners/form.html',
                           titulo='Editar banner', banner=banner,
                           posiciones=POSICIONES, posicion_info=POSICION_INFO)


# ── Admin: toggle activo ──────────────────────────────────────────────────────

@banners_bp.route('/admin/banners/<int:banner_id>/toggle', methods=['POST'])
@login_required
@requiere_funcion()
def admin_banner_toggle(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    banner.activo = not banner.activo
    db.session.commit()
    estado = 'activado' if banner.activo else 'desactivado'
    flash(f'Banner "{banner.titulo}" {estado}.', 'success')
    return redirect(url_for('banners_bp.admin_banners'))


# ── Admin: eliminar ───────────────────────────────────────────────────────────

@banners_bp.route('/admin/banners/<int:banner_id>/eliminar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_banner_eliminar(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    nombre = banner.titulo
    _eliminar_imagen(banner_id)
    db.session.delete(banner)
    db.session.commit()
    flash(f'Banner "{nombre}" eliminado.', 'success')
    return redirect(url_for('banners_bp.admin_banners'))


# ── Click tracking (público) ──────────────────────────────────────────────────

@banners_bp.route('/b/<int:banner_id>')
def banner_click(banner_id):
    """Registra el click e inmediatamente redirige a la URL destino."""
    banner = Banner.query.get_or_404(banner_id)
    if banner.url_destino:
        banner.clicks += 1
        db.session.commit()
        return redirect(banner.url_destino)
    return redirect(url_for('main_bp.index'))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(value):
    from datetime import date
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
