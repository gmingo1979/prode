# app/routes/grupos.py
#
# Grupos privados entre usuarios del Prode.
#
# GET  /prode/mis-grupos               → lista de grupos del usuario
# GET/POST /prode/grupos/crear         → crear grupo
# GET  /prode/grupos/<id>              → detalle + ranking del grupo
# GET  /prode/grupos/<id>/invitar      → formulario invitación (modal)
# POST /prode/grupos/<id>/invitar      → enviar invitación por mail
# GET/POST /prode/grupos/unirse        → unirse por código
# GET  /prode/invitacion/<token>       → aceptar invitación por link
# POST /prode/grupos/<id>/salir        → abandonar grupo
# POST /prode/grupos/<id>/remover/<uid>→ remover miembro (solo creador)

import re

from flask import (Blueprint, abort, flash, redirect,
                   render_template, request, session, url_for)
from flask_login import current_user, login_required

from sqlalchemy.orm import joinedload

from app.db import db
from app.models.grupo import ProdeGrupo, ProdeGrupoInvitacion, ProdeGrupoMiembro
from app.models.usuario import Usuario

grupos_bp = Blueprint('grupos_bp', __name__, url_prefix='/prode')

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unir_usuario_a_grupo(grupo, usuario, origen='codigo'):
    """Agrega al usuario como miembro si no lo es ya. Devuelve True si se agregó."""
    if grupo.es_miembro(usuario.id):
        return False
    db.session.add(ProdeGrupoMiembro(
        grupo_id   = grupo.id,
        usuario_id = usuario.id,
        rol        = 'miembro',
    ))
    db.session.commit()
    return True


def _ranking_grupo(torneo_id, ids_miembros):
    """Filtra el ranking global de un torneo a los miembros del grupo."""
    from app.utils.prode_puntaje import obtener_ranking_torneo
    ranking_global = obtener_ranking_torneo(torneo_id)
    return [r for r in ranking_global if r['usuario_id'] in ids_miembros]


def _torneos_del_grupo(ids_miembros):
    """
    Devuelve torneos donde al menos un miembro está inscripto y aprobado.
    """
    from app.models.prode import ProdeInscripcion, ProdeTorneo
    torneos_ids = (
        db.session.query(ProdeInscripcion.torneo_id)
        .filter(
            ProdeInscripcion.usuario_id.in_(ids_miembros),
            ProdeInscripcion.estado == 'aprobado',
        )
        .distinct()
        .all()
    )
    ids = [t[0] for t in torneos_ids]
    return ProdeTorneo.query.filter(ProdeTorneo.id.in_(ids), ProdeTorneo.activo == True).all()


# ── Mis grupos ────────────────────────────────────────────────────────────────

@grupos_bp.route('/mis-grupos')
@login_required
def mis_grupos():
    membresias = (
        ProdeGrupoMiembro.query
        .filter_by(usuario_id=current_user.id)
        .options(joinedload(ProdeGrupoMiembro.grupo).joinedload(ProdeGrupo.miembros))
        .order_by(ProdeGrupoMiembro.joined_at.desc())
        .all()
    )
    grupos = [m.grupo for m in membresias]
    return render_template(
        'prode/grupos/mis_grupos.html',
        titulo = 'Mis grupos',
        grupos = grupos,
    )


# ── Crear grupo ───────────────────────────────────────────────────────────────

@grupos_bp.route('/grupos/crear', methods=['GET', 'POST'])
@login_required
def crear_grupo():
    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()

        if not nombre:
            flash('El nombre del grupo es obligatorio.', 'danger')
            return render_template('prode/grupos/crear.html', titulo='Crear grupo')

        if len(nombre) > 80:
            flash('El nombre no puede superar 80 caracteres.', 'danger')
            return render_template('prode/grupos/crear.html', titulo='Crear grupo')

        grupo = ProdeGrupo(
            nombre      = nombre,
            descripcion = descripcion or None,
            creador_id  = current_user.id,
        )
        db.session.add(grupo)
        db.session.flush()  # obtener grupo.id antes del commit

        # El creador es el primer miembro
        db.session.add(ProdeGrupoMiembro(
            grupo_id   = grupo.id,
            usuario_id = current_user.id,
            rol        = 'creador',
        ))
        db.session.commit()

        flash(f'Grupo "{grupo.nombre}" creado. Código: {grupo.codigo}', 'success')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo.id))

    return render_template('prode/grupos/crear.html', titulo='Crear grupo')


# ── Detalle del grupo ─────────────────────────────────────────────────────────

@grupos_bp.route('/grupos/<int:grupo_id>')
@login_required
def detalle(grupo_id):
    grupo = (
        ProdeGrupo.query
        .options(joinedload(ProdeGrupo.miembros).joinedload(ProdeGrupoMiembro.usuario))
        .get_or_404(grupo_id)
    )

    if not grupo.es_miembro(current_user.id):
        flash('No pertenecés a ese grupo.', 'warning')
        return redirect(url_for('grupos_bp.mis_grupos'))

    ids_miembros = {m.usuario_id for m in grupo.miembros}
    torneos      = _torneos_del_grupo(ids_miembros)

    # Torneo seleccionado (por query param o el primero)
    torneo_id_sel = request.args.get('torneo_id', type=int)
    torneo_sel    = None
    ranking       = []

    if torneos:
        torneo_sel = next((t for t in torneos if t.id == torneo_id_sel), torneos[0])
        ranking    = _ranking_grupo(torneo_sel.id, ids_miembros)

    es_creador = (grupo.creador_id == current_user.id)

    return render_template(
        'prode/grupos/detalle.html',
        titulo      = grupo.nombre,
        grupo       = grupo,
        torneos     = torneos,
        torneo_sel  = torneo_sel,
        ranking     = ranking,
        es_creador  = es_creador,
        usuario_id  = current_user.id,
    )


# ── Invitar ───────────────────────────────────────────────────────────────────

@grupos_bp.route('/grupos/<int:grupo_id>/invitar', methods=['POST'])
@login_required
def invitar(grupo_id):
    grupo = ProdeGrupo.query.get_or_404(grupo_id)

    if not grupo.es_miembro(current_user.id):
        abort(403)

    email = request.form.get('email', '').strip().lower()

    if not _EMAIL_RE.match(email):
        flash('Email inválido.', 'danger')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))

    # ¿Ya es miembro?
    usuario_existente = Usuario.query.filter_by(email=email).first()
    if usuario_existente and grupo.es_miembro(usuario_existente.id):
        flash(f'{email} ya es miembro del grupo.', 'info')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))

    # ¿Ya tiene invitación pendiente?
    inv_existente = ProdeGrupoInvitacion.query.filter_by(
        grupo_id=grupo_id,
        email=email,
        estado='pendiente',
    ).first()
    if inv_existente:
        flash(f'Ya existe una invitación pendiente para {email}.', 'info')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))

    invitacion = ProdeGrupoInvitacion(
        grupo_id       = grupo_id,
        email          = email,
        invitado_por_id = current_user.id,
    )
    db.session.add(invitacion)
    db.session.commit()

    es_nuevo = (usuario_existente is None)

    from app.services.grupos_mail import enviar_invitacion
    enviar_invitacion(invitacion, es_nuevo_usuario=es_nuevo)

    flash(f'Invitación enviada a {email}.', 'success')
    return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))


# ── Unirse por código ─────────────────────────────────────────────────────────

@grupos_bp.route('/grupos/unirse', methods=['GET', 'POST'])
@login_required
def unirse_codigo():
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()

        if not codigo:
            flash('Ingresá el código del grupo.', 'danger')
            return render_template('prode/grupos/unirse.html', titulo='Unirme a un grupo')

        grupo = ProdeGrupo.query.filter_by(codigo=codigo).first()
        if not grupo:
            flash('Código incorrecto. Verificalo con quien te invitó.', 'danger')
            return render_template('prode/grupos/unirse.html', titulo='Unirme a un grupo')

        if grupo.es_miembro(current_user.id):
            flash('Ya sos miembro de ese grupo.', 'info')
            return redirect(url_for('grupos_bp.detalle', grupo_id=grupo.id))

        _unir_usuario_a_grupo(grupo, current_user, origen='codigo')

        from app.services.grupos_mail import notificar_nuevo_miembro
        notificar_nuevo_miembro(grupo, current_user)

        flash(f'¡Te uniste a "{grupo.nombre}"!', 'success')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo.id))

    # Pre-fill del código si viene por GET (ej: desde un link con ?codigo=XXXX)
    codigo_param = request.args.get('codigo', '')
    return render_template(
        'prode/grupos/unirse.html',
        titulo       = 'Unirme a un grupo',
        codigo_param = codigo_param,
    )


# ── Aceptar invitación por link ───────────────────────────────────────────────

@grupos_bp.route('/invitacion/<token>')
def aceptar_invitacion(token):
    invitacion = ProdeGrupoInvitacion.query.filter_by(token=token).first_or_404()

    if invitacion.estado == 'aceptada':
        flash('Esta invitación ya fue utilizada.', 'info')
        if current_user.is_authenticated:
            return redirect(url_for('grupos_bp.detalle', grupo_id=invitacion.grupo_id))
        return redirect(url_for('auth_bp.login'))

    # Guardar token en sesión para usarlo después del login/registro
    session['inv_token'] = token

    if not current_user.is_authenticated:
        flash('Iniciá sesión o creá una cuenta para unirte al grupo.', 'info')
        return redirect(url_for('auth_bp.login',
                                next=url_for('grupos_bp.aceptar_invitacion', token=token)))

    # Ya autenticado → unir directamente
    return _procesar_invitacion(invitacion, current_user)


def _procesar_invitacion(invitacion, usuario):
    """Une al usuario al grupo y marca la invitación como aceptada."""
    grupo = invitacion.grupo

    if not grupo.es_miembro(usuario.id):
        _unir_usuario_a_grupo(grupo, usuario, origen='invitacion')
        from app.services.grupos_mail import notificar_nuevo_miembro
        notificar_nuevo_miembro(grupo, usuario)

    invitacion.estado = 'aceptada'
    db.session.commit()

    session.pop('inv_token', None)
    flash(f'¡Te uniste al grupo "{grupo.nombre}"!', 'success')
    return redirect(url_for('grupos_bp.detalle', grupo_id=grupo.id))


# ── Salir del grupo ───────────────────────────────────────────────────────────

@grupos_bp.route('/grupos/<int:grupo_id>/salir', methods=['POST'])
@login_required
def salir(grupo_id):
    grupo = ProdeGrupo.query.get_or_404(grupo_id)

    if grupo.creador_id == current_user.id:
        flash('El creador no puede abandonar el grupo. Podés eliminarlo si ya no lo necesitás.', 'warning')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))

    membresia = ProdeGrupoMiembro.query.filter_by(
        grupo_id=grupo_id,
        usuario_id=current_user.id,
    ).first()
    if membresia:
        db.session.delete(membresia)
        db.session.commit()
        flash(f'Saliste del grupo "{grupo.nombre}".', 'success')

    return redirect(url_for('grupos_bp.mis_grupos'))


# ── Remover miembro (solo creador) ────────────────────────────────────────────

@grupos_bp.route('/grupos/<int:grupo_id>/remover/<int:usuario_id>', methods=['POST'])
@login_required
def remover_miembro(grupo_id, usuario_id):
    grupo = ProdeGrupo.query.get_or_404(grupo_id)

    if grupo.creador_id != current_user.id:
        abort(403)

    if usuario_id == current_user.id:
        flash('No podés removerte a vos mismo.', 'warning')
        return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))

    membresia = ProdeGrupoMiembro.query.filter_by(
        grupo_id=grupo_id,
        usuario_id=usuario_id,
    ).first_or_404()

    usuario_removido = membresia.usuario
    db.session.delete(membresia)
    db.session.commit()

    from app.services.grupos_mail import notificar_expulsion
    notificar_expulsion(grupo, usuario_removido)

    flash(f'{usuario_removido.nombre_completo} fue removido del grupo.', 'success')
    return redirect(url_for('grupos_bp.detalle', grupo_id=grupo_id))


# ── Eliminar grupo (solo creador) ─────────────────────────────────────────────

@grupos_bp.route('/grupos/<int:grupo_id>/eliminar', methods=['POST'])
@login_required
def eliminar_grupo(grupo_id):
    grupo = ProdeGrupo.query.get_or_404(grupo_id)

    if grupo.creador_id != current_user.id:
        abort(403)

    db.session.delete(grupo)
    db.session.commit()
    flash(f'El grupo "{grupo.nombre}" fue eliminado.', 'success')
    return redirect(url_for('grupos_bp.mis_grupos'))
