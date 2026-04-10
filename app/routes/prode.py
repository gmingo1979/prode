# app/routes/prode.py
#
# Módulo Prode — blueprint único.
#
# RUTAS USUARIOS:
#   GET  /prode/                              → hub (torneos disponibles)
#   POST /prode/<torneo_id>/inscribirse       → solicitar inscripción
#   GET  /prode/<torneo_id>/pronosticos       → pronosticar partidos del torneo
#   POST /prode/<torneo_id>/pronosticos       → guardar pronósticos
#   GET  /prode/<torneo_id>/ranking           → ranking del torneo
#
# RUTAS ADMIN (requieren función RBAC):
#   Torneos   : listar / nuevo / editar / activar
#   Fases     : nuevo / editar / eliminar
#   Equipos   : nuevo / editar / eliminar
#   Partidos  : nuevo / editar / cerrar
#   Inscripciones: listar pendientes / aprobar / rechazar

from datetime import date, datetime, timezone, timedelta
from flask import (Blueprint, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from app.db import db
from app.models.prode import (ProdeConfigPuntaje, ProdeEquipo, ProdeFase,
                               ProdeInscripcion, ProdePartido, ProdePronostico,
                               ProdeTorneo)
from app.utils.permisos import requiere_funcion
from app.utils.prode_puntaje import calcular_puntos, obtener_ranking_torneo

prode_bp = Blueprint('prode_bp', __name__, url_prefix='/prode')


# =================================================================
# HELPERS
# =================================================================

def _get_inscripcion(torneo_id):
    """Devuelve la inscripción del usuario actual para el torneo, o None."""
    return ProdeInscripcion.query.filter_by(
        usuario_id=current_user.id,
        torneo_id=torneo_id,
    ).first()


def _esta_aprobado(torneo_id) -> bool:
    insc = _get_inscripcion(torneo_id)
    return insc is not None and insc.estado == 'aprobado'


# =================================================================
# HUB — página principal del Prode
# =================================================================

@prode_bp.route('/')
@login_required
def index():
    """Lista los torneos activos con el estado de inscripción del usuario."""
    torneos = ProdeTorneo.query.filter_by(activo=True)\
                               .order_by(ProdeTorneo.fecha_inicio.desc()).all()

    inscripciones = ProdeInscripcion.query.filter_by(usuario_id=current_user.id).all()
    mis_inscripciones     = {i.torneo_id: i.estado for i in inscripciones}
    mis_inscripciones_obj = {i.torneo_id: i        for i in inscripciones}

    from datetime import date
    return render_template('prode/index.html',
                           titulo='Prode',
                           torneos=torneos,
                           mis_inscripciones=mis_inscripciones,
                           mis_inscripciones_obj=mis_inscripciones_obj,
                           today=date.today())


# =================================================================
# INSCRIPCIÓN
# =================================================================

@prode_bp.route('/<int:torneo_id>/inscribirse', methods=['POST'])
@login_required
def inscribirse(torneo_id):
    from flask import current_app
    torneo = ProdeTorneo.query.get_or_404(torneo_id)

    if not torneo.inscripcion_abierta:
        flash('La inscripción para este torneo está cerrada.', 'warning')
        return redirect(url_for('prode_bp.index'))

    existente = _get_inscripcion(torneo_id)
    if existente:
        # Si tiene un pago pendiente, redirigir al checkout de nuevo
        if existente.estado == 'pago_pendiente' and existente.mp_preference_id:
            import mercadopago
            sdk = mercadopago.SDK(current_app.config['MP_ACCESS_TOKEN'])
            pref = sdk.preference().get(existente.mp_preference_id)
            init_point = pref.get('response', {}).get('init_point')
            if init_point:
                return redirect(init_point)
        flash('Ya tenés una solicitud de inscripción para este torneo.', 'info')
        return redirect(url_for('prode_bp.index'))

    precio = float(torneo.precio_inscripcion or 0)

    # ── Torneo gratuito: inscripción directa pendiente de aprobación admin ──
    if precio == 0:
        insc = ProdeInscripcion(usuario_id=current_user.id,
                                torneo_id=torneo_id,
                                estado='pendiente')
        db.session.add(insc)
        db.session.commit()
        flash(f'Solicitud enviada para <strong>{torneo.nombre}</strong>. '
              'Un administrador la aprobará pronto.', 'success')
        return redirect(url_for('prode_bp.index'))

    # ── Torneo pago: crear preference en MercadoPago ────────────────────────
    import mercadopago

    mp_token = current_app.config.get('MP_ACCESS_TOKEN', '')
    if not mp_token:
        flash('El pago no está configurado. Contactá al administrador.', 'danger')
        return redirect(url_for('prode_bp.index'))

    # Crear inscripción en estado pago_pendiente antes de ir a MP
    insc = ProdeInscripcion(usuario_id=current_user.id,
                            torneo_id=torneo_id,
                            estado='pago_pendiente')
    db.session.add(insc)
    db.session.flush()  # necesitamos el id antes del commit

    base_url = current_app.config.get('BASE_URL', request.host_url.rstrip('/'))
    sdk = mercadopago.SDK(mp_token)

    success_url = f"{base_url}{url_for('prode_bp.pago_success')}"
    failure_url = f"{base_url}{url_for('prode_bp.pago_failure')}"
    pending_url = f"{base_url}{url_for('prode_bp.pago_pending')}"

    preference_data = {
        "items": [{
            "id":          f"torneo-{torneo_id}",
            "title":       f"Inscripción — {torneo.nombre}",
            "quantity":    1,
            "unit_price":  precio,
            "currency_id": "ARS",
        }],
        "payer": {
            "name":    current_user.nombre,
            "surname": current_user.apellido,
            "email":   current_user.email or "",
        },
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "external_reference":   str(insc.id),
        "statement_descriptor": "PRODE",
    }

    # auto_return solo funciona con HTTPS (requerido por MP en producción)
    if base_url.startswith("https://"):
        preference_data["auto_return"] = "approved"

    # notification_url solo si es accesible públicamente (no localhost)
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        preference_data["notification_url"] = f"{base_url}{url_for('prode_bp.pago_webhook')}"

    try:
        resp = sdk.preference().create(preference_data)
        preference = resp.get('response', {})
        init_point = preference.get('init_point')
        if not init_point:
            raise ValueError(f"Sin init_point: {resp}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"MP preference error: {e}")
        flash('No se pudo iniciar el pago. Intentá de nuevo.', 'danger')
        return redirect(url_for('prode_bp.index'))

    insc.mp_preference_id = preference['id']
    db.session.commit()

    return redirect(init_point)


# ── Callbacks de MercadoPago ───────────────────────────────────────────────

@prode_bp.route('/pago/success')
@login_required
def pago_success():
    """MP redirige acá cuando el pago fue aprobado."""
    payment_id       = request.args.get('payment_id')
    status           = request.args.get('status')
    external_ref     = request.args.get('external_reference')
    merchant_order   = request.args.get('merchant_order_id')

    insc = None
    if external_ref and external_ref.isdigit():
        insc = ProdeInscripcion.query.get(int(external_ref))

    if insc and status == 'approved':
        insc.estado        = 'aprobado'
        insc.mp_payment_id = payment_id
        insc.mp_status     = status
        db.session.commit()
        flash(f'¡Pago aprobado! Ya estás inscripto en <strong>{insc.torneo.nombre}</strong>.', 'success')
    elif insc:
        insc.mp_payment_id = payment_id
        insc.mp_status     = status
        db.session.commit()
        flash('El pago está siendo procesado. Te avisaremos cuando se confirme.', 'info')

    return redirect(url_for('prode_bp.index'))


@prode_bp.route('/pago/failure')
@login_required
def pago_failure():
    """MP redirige acá cuando el pago falló o fue rechazado."""
    external_ref = request.args.get('external_reference')
    if external_ref and external_ref.isdigit():
        insc = ProdeInscripcion.query.get(int(external_ref))
        if insc and insc.estado == 'pago_pendiente':
            insc.mp_status = 'rejected'
            db.session.commit()
    flash('El pago no pudo completarse. Podés intentar nuevamente.', 'danger')
    return redirect(url_for('prode_bp.index'))


@prode_bp.route('/pago/pending')
@login_required
def pago_pending():
    """MP redirige acá para pagos en proceso (ej: transferencia bancaria)."""
    flash('Tu pago está pendiente de acreditación. Te confirmaremos la inscripción cuando se acredite.', 'info')
    return redirect(url_for('prode_bp.index'))


@prode_bp.route('/pago/verificar/<int:insc_id>', methods=['POST'])
@login_required
def pago_verificar(insc_id):
    """
    El usuario ya pagó en MP pero el callback no llegó (ej: localhost sin auto_return).
    Consulta directamente a MP si el pago fue aprobado y actualiza la inscripción.
    """
    from flask import current_app
    import mercadopago

    insc = ProdeInscripcion.query.get_or_404(insc_id)

    # Solo el dueño de la inscripción puede verificar
    if insc.usuario_id != current_user.id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('prode_bp.index'))

    if insc.estado == 'aprobado':
        flash('Tu inscripción ya está aprobada.', 'info')
        return redirect(url_for('prode_bp.index'))

    mp_token = current_app.config.get('MP_ACCESS_TOKEN', '')
    if not mp_token or not insc.mp_preference_id:
        flash('No se pudo verificar el pago. Contactá al administrador.', 'danger')
        return redirect(url_for('prode_bp.index'))

    try:
        sdk = mercadopago.SDK(mp_token)
        # Buscar pagos por external_reference (id de la inscripción)
        result = sdk.payment().search({
            "external_reference": str(insc.id),
            "sort":               "date_created",
            "criteria":           "desc",
        })
        payments = result.get('response', {}).get('results', [])

        aprobado = any(p.get('status') == 'approved' for p in payments)

        if aprobado:
            payment = next(p for p in payments if p.get('status') == 'approved')
            insc.estado        = 'aprobado'
            insc.mp_payment_id = str(payment.get('id', ''))
            insc.mp_status     = 'approved'
            db.session.commit()
            flash(f'¡Pago verificado! Ya estás inscripto en <strong>{insc.torneo.nombre}</strong>.', 'success')
        elif payments:
            insc.mp_status = payments[0].get('status', '')
            db.session.commit()
            flash(f'El pago figura como <strong>{insc.mp_status}</strong>. Si completaste el pago esperá unos minutos e intentá de nuevo.', 'warning')
        else:
            flash('No encontramos pagos asociados. Si ya pagaste, esperá unos minutos e intentá de nuevo.', 'warning')

    except Exception as e:
        current_app.logger.error(f"MP verificar error: {e}")
        flash('No se pudo consultar el estado del pago. Intentá de nuevo.', 'danger')

    return redirect(url_for('prode_bp.index'))


@prode_bp.route('/pago/webhook', methods=['POST'])
def pago_webhook():
    """
    Notificación server-to-server de MercadoPago.
    MP llama a esta URL cada vez que cambia el estado de un pago.
    No requiere login — MP llama directamente.
    """
    from flask import current_app
    import mercadopago

    data = request.get_json(silent=True) or {}
    topic = data.get('type') or request.args.get('topic', '')

    if topic != 'payment':
        return '', 200

    payment_id = (data.get('data', {}).get('id')
                  or request.args.get('id'))
    if not payment_id:
        return '', 200

    mp_token = current_app.config.get('MP_ACCESS_TOKEN', '')
    if not mp_token:
        return '', 200

    try:
        sdk = mercadopago.SDK(mp_token)
        payment_info = sdk.payment().get(payment_id)
        payment = payment_info.get('response', {})

        external_ref = payment.get('external_reference')
        status       = payment.get('status')

        if external_ref and external_ref.isdigit():
            insc = ProdeInscripcion.query.get(int(external_ref))
            if insc:
                insc.mp_payment_id = str(payment_id)
                insc.mp_status     = status
                if status == 'approved':
                    insc.estado = 'aprobado'
                elif status in ('rejected', 'cancelled'):
                    insc.estado = 'pago_pendiente'  # puede reintentar
                db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Webhook MP error: {e}")
        return '', 500

    return '', 200


# =================================================================
# PRONÓSTICOS
# =================================================================

@prode_bp.route('/<int:torneo_id>/pronosticos', methods=['GET', 'POST'])
@login_required
def pronosticos(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)

    if not _esta_aprobado(torneo_id):
        flash('Necesitás estar inscripto y aprobado para pronosticar.', 'warning')
        return redirect(url_for('prode_bp.index'))

    fases = ProdeFase.query.filter_by(torneo_id=torneo_id)\
                           .order_by(ProdeFase.orden).all()

    mis_pronosticos = {
        p.partido_id: p
        for p in ProdePronostico.query.filter_by(usuario_id=current_user.id).all()
    }

    todos_partidos = [p for fase in fases for p in fase.partidos]

    if request.method == 'POST':
        guardados = 0
        bloqueados = 0

        for partido in todos_partidos:
            if partido.pronosticos_bloqueados:
                bloqueados += 1
                continue

            gl_str = request.form.get(f'local_{partido.id}', '').strip()
            gv_str = request.form.get(f'visitante_{partido.id}', '').strip()

            if gl_str == '' or gv_str == '':
                continue

            try:
                gl = int(gl_str)
                gv = int(gv_str)
                if gl < 0 or gv < 0:
                    continue
            except ValueError:
                continue

            pron = mis_pronosticos.get(partido.id)
            if pron:
                pron.goles_local     = gl
                pron.goles_visitante = gv
            else:
                pron = ProdePronostico(
                    usuario_id      = current_user.id,
                    partido_id      = partido.id,
                    goles_local     = gl,
                    goles_visitante = gv,
                    puntos          = 0,
                )
                db.session.add(pron)
                mis_pronosticos[partido.id] = pron
            guardados += 1

        db.session.commit()

        cant = guardados
        msg = f'{cant} pronóstico{"s" if cant != 1 else ""} guardado{"s" if cant != 1 else ""}.'
        if bloqueados:
            msg += f' ({bloqueados} partido{"s" if bloqueados != 1 else ""} ya bloqueado{"s" if bloqueados != 1 else ""})'
        flash(msg, 'success')
        return redirect(url_for('prode_bp.pronosticos', torneo_id=torneo_id))

    ahora = datetime.now(timezone.utc)

    # ── Agrupar partidos por fecha (solo con equipos reales) ─────────────
    from collections import defaultdict

    def es_partido_real(p):
        return (not p.equipo_local.nombre.startswith('Por definir') and
                not p.equipo_visitante.nombre.startswith('Por definir'))

    por_fecha = defaultdict(list)
    for p in sorted(todos_partidos, key=lambda x: x.fecha_hora):
        if es_partido_real(p):
            por_fecha[p.fecha_hora.date()].append(p)

    fechas_ordenadas = sorted(por_fecha.keys())

    # ── Resumen urgente ────────────────────────────────────────────────────
    pendientes_urgentes = [
        p for p in todos_partidos
        if not p.pronosticos_bloqueados
        and p.id not in mis_pronosticos
        and es_partido_real(p)
    ]

    limite_24h = ahora + timedelta(hours=24)
    en_24h = []
    for p in todos_partidos:
        if not p.pronosticos_bloqueados and es_partido_real(p):
            fh = p.fecha_hora.replace(tzinfo=timezone.utc) if p.fecha_hora.tzinfo is None else p.fecha_hora
            if fh - timedelta(hours=2) <= limite_24h:
                en_24h.append(p)

    partidos_reales     = [p for p in todos_partidos if es_partido_real(p)]
    total_disponibles   = sum(1 for p in partidos_reales if not p.pronosticos_bloqueados)
    total_pronosticados = sum(1 for p in partidos_reales
                              if not p.pronosticos_bloqueados and p.id in mis_pronosticos)

    tab_activa = next(
        (f for f in fechas_ordenadas
         if any(not p.pronosticos_bloqueados for p in por_fecha[f])),
        fechas_ordenadas[0] if fechas_ordenadas else None
    )

    faltan_por_fecha = {
        fecha: sum(1 for p in partidos_dia
                   if not p.pronosticos_bloqueados and p.id not in mis_pronosticos)
        for fecha, partidos_dia in por_fecha.items()
    }

    return render_template('prode/pronosticos/index.html',
                           titulo=f'Pronósticos — {torneo.nombre}',
                           torneo=torneo,
                           por_fecha=por_fecha,
                           fechas_ordenadas=fechas_ordenadas,
                           mis_pronosticos=mis_pronosticos,
                           faltan_por_fecha=faltan_por_fecha,
                           tab_activa=tab_activa,
                           pendientes_urgentes=pendientes_urgentes,
                           en_24h=en_24h,
                           total_disponibles=total_disponibles,
                           total_pronosticados=total_pronosticados,
                           ahora=ahora)


# =================================================================
# RANKING
# =================================================================

@prode_bp.route('/<int:torneo_id>/ranking')
@login_required
def ranking_torneo(torneo_id):
    torneo  = ProdeTorneo.query.get_or_404(torneo_id)
    ranking = obtener_ranking_torneo(torneo_id)

    return render_template('prode/ranking/index.html',
                           titulo=f'Ranking — {torneo.nombre}',
                           torneo=torneo,
                           ranking=ranking,
                           usuario_logueado_id=current_user.id,
                           sector_actual=None,
                           sectores=[])


# =================================================================
# DASHBOARD PERSONAL
# =================================================================

@prode_bp.route('/<int:torneo_id>/dashboard')
@login_required
def dashboard(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)

    if not _esta_aprobado(torneo_id):
        flash('Necesitás estar inscripto y aprobado.', 'warning')
        return redirect(url_for('prode_bp.index'))

    ahora = datetime.now(timezone.utc)

    # ── Todos los partidos del torneo ─────────────────────────────────────
    todos_partidos = [p for fase in torneo.fases for p in fase.partidos]

    mis_pronosticos = {
        p.partido_id: p
        for p in ProdePronostico.query.filter_by(usuario_id=current_user.id).all()
    }

    def es_real(p):
        return (not p.equipo_local.nombre.startswith('Por definir') and
                not p.equipo_visitante.nombre.startswith('Por definir'))

    partidos_reales = [p for p in todos_partidos if es_real(p)]

    # ── Próximo partido a jugar (no bloqueado aún) ────────────────────────
    proximo = None
    for p in sorted(partidos_reales, key=lambda x: x.fecha_hora):
        if p.estado == 'pendiente':
            fh = p.fecha_hora.replace(tzinfo=timezone.utc) if p.fecha_hora.tzinfo is None else p.fecha_hora
            if fh > ahora:
                proximo = p
                break

    # ── Posición en el ranking ────────────────────────────────────────────
    ranking = obtener_ranking_torneo(torneo_id)
    mi_posicion = next((r for r in ranking if r['usuario_id'] == current_user.id), None)

    # ── Últimos 5 partidos cerrados con mi pronóstico ─────────────────────
    cerrados = sorted(
        [p for p in partidos_reales if p.estado == 'cerrado'],
        key=lambda x: x.fecha_hora, reverse=True
    )
    ultimos_resultados = []
    for p in cerrados[:10]:
        pron = mis_pronosticos.get(p.id)
        ultimos_resultados.append({'partido': p, 'pronostico': pron})
        if len(ultimos_resultados) == 5:
            break

    # ── Racha actual ──────────────────────────────────────────────────────
    # Recorre cerrados del más reciente al más antiguo
    pts_parcial = torneo.config.resultado_parcial if torneo.config else 1
    racha_actual = 0
    racha_tipo   = None  # 'buena' | 'mala' | None

    for p in cerrados:
        pron = mis_pronosticos.get(p.id)
        if not pron:
            break
        if pron.puntos >= pts_parcial:
            if racha_tipo == 'mala':
                break
            racha_tipo = 'buena'
            racha_actual += 1
        else:
            if racha_tipo == 'buena':
                break
            racha_tipo = 'mala'
            racha_actual += 1

    # ── Estadísticas generales ────────────────────────────────────────────
    pts_exacto  = torneo.config.resultado_exacto  if torneo.config else 3

    total_cerrados    = len(cerrados)
    con_pronostico    = sum(1 for p in cerrados if p.id in mis_pronosticos)
    exactos           = sum(1 for p in cerrados
                            if mis_pronosticos.get(p.id)
                            and mis_pronosticos[p.id].puntos == pts_exacto)
    aciertos          = sum(1 for p in cerrados
                            if mis_pronosticos.get(p.id)
                            and mis_pronosticos[p.id].puntos >= pts_parcial)
    puntos_totales    = sum(
        (mis_pronosticos[p.id].puntos or 0)
        for p in cerrados if p.id in mis_pronosticos
    )

    # ── Partidos sin pronosticar aún disponibles ──────────────────────────
    pendientes = [
        p for p in partidos_reales
        if not p.pronosticos_bloqueados and p.id not in mis_pronosticos
    ]

    # ── Próximos a bloquearse (< 6h) ──────────────────────────────────────
    urgentes = []
    for p in partidos_reales:
        if not p.pronosticos_bloqueados and p.id not in mis_pronosticos:
            fh = p.fecha_hora.replace(tzinfo=timezone.utc) if p.fecha_hora.tzinfo is None else p.fecha_hora
            if fh - timedelta(hours=2) <= ahora + timedelta(hours=6):
                urgentes.append(p)

    return render_template('prode/dashboard/index.html',
                           titulo=f'Mi dashboard — {torneo.nombre}',
                           torneo=torneo,
                           ahora=ahora,
                           proximo=proximo,
                           mi_posicion=mi_posicion,
                           ranking_total=len(ranking),
                           ultimos_resultados=ultimos_resultados,
                           racha_actual=racha_actual,
                           racha_tipo=racha_tipo,
                           total_cerrados=total_cerrados,
                           con_pronostico=con_pronostico,
                           exactos=exactos,
                           aciertos=aciertos,
                           puntos_totales=puntos_totales,
                           pendientes=pendientes,
                           urgentes=urgentes,
                           pts_exacto=pts_exacto,
                           pts_parcial=pts_parcial)


# =================================================================
# HISTORIAL PERSONAL
# =================================================================

@prode_bp.route('/<int:torneo_id>/historial')
@login_required
def historial(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)

    if not _esta_aprobado(torneo_id):
        flash('Necesitás estar inscripto y aprobado.', 'warning')
        return redirect(url_for('prode_bp.index'))

    mis_pronosticos = {
        p.partido_id: p
        for p in ProdePronostico.query.filter_by(usuario_id=current_user.id).all()
    }

    pts_exacto  = torneo.config.resultado_exacto  if torneo.config else 3
    pts_parcial = torneo.config.resultado_parcial if torneo.config else 1

    todos_partidos = [p for fase in torneo.fases for p in fase.partidos]

    def es_real(p):
        return (not p.equipo_local.nombre.startswith('Por definir') and
                not p.equipo_visitante.nombre.startswith('Por definir'))

    cerrados = sorted(
        [p for p in todos_partidos if p.estado == 'cerrado' and es_real(p)],
        key=lambda x: x.fecha_hora, reverse=True
    )

    historial_items = []
    for p in cerrados:
        pron = mis_pronosticos.get(p.id)
        if pron:
            if pron.puntos == pts_exacto:
                resultado = 'exacto'
            elif pron.puntos >= pts_parcial:
                resultado = 'parcial'
            else:
                resultado = 'errado'
        else:
            resultado = 'sin_pronostico'
        historial_items.append({'partido': p, 'pronostico': pron, 'resultado': resultado})

    total     = len(cerrados)
    exactos   = sum(1 for h in historial_items if h['resultado'] == 'exacto')
    parciales = sum(1 for h in historial_items if h['resultado'] == 'parcial')
    errados   = sum(1 for h in historial_items if h['resultado'] == 'errado')
    sin_pron  = sum(1 for h in historial_items if h['resultado'] == 'sin_pronostico')
    puntos_tot = sum((h['pronostico'].puntos or 0) for h in historial_items if h['pronostico'])
    pct_acierto = round((exactos + parciales) / total * 100) if total > 0 else 0

    # Racha actual (más reciente primero)
    racha_actual = 0
    racha_tipo   = None
    for h in historial_items:
        if h['resultado'] == 'sin_pronostico':
            break
        if h['resultado'] in ('exacto', 'parcial'):
            if racha_tipo == 'mala': break
            racha_tipo = 'buena'; racha_actual += 1
        else:
            if racha_tipo == 'buena': break
            racha_tipo = 'mala'; racha_actual += 1

    # Rachas máximas (más antiguo primero)
    racha_max_buena = racha_max_mala = 0
    cb = cm = 0
    for h in reversed(historial_items):
        if h['resultado'] in ('exacto', 'parcial'):
            cb += 1; cm = 0
        elif h['resultado'] == 'errado':
            cm += 1; cb = 0
        else:
            cb = 0; cm = 0
        racha_max_buena = max(racha_max_buena, cb)
        racha_max_mala  = max(racha_max_mala,  cm)

    # Agrupar por fase
    por_fase = {}
    for h in historial_items:
        fn = h['partido'].fase.nombre
        if fn not in por_fase:
            por_fase[fn] = []
        por_fase[fn].append(h)

    return render_template('prode/historial/index.html',
                           titulo=f'Mi historial — {torneo.nombre}',
                           torneo=torneo,
                           historial=historial_items,
                           por_fase=por_fase,
                           total=total,
                           exactos=exactos,
                           parciales=parciales,
                           errados=errados,
                           sin_pron=sin_pron,
                           puntos_tot=puntos_tot,
                           pct_acierto=pct_acierto,
                           racha_actual=racha_actual,
                           racha_tipo=racha_tipo,
                           racha_max_buena=racha_max_buena,
                           racha_max_mala=racha_max_mala,
                           pts_exacto=pts_exacto,
                           pts_parcial=pts_parcial)


# =================================================================
# ADMIN — TORNEOS
# =================================================================

# =================================================================
# TABLA DE POSICIONES POR GRUPOS
# =================================================================

@prode_bp.route('/<int:torneo_id>/grupos')
@login_required
def tabla_grupos(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)

    if not _esta_aprobado(torneo_id):
        flash('Necesitás estar inscripto y aprobado para ver la tabla.', 'warning')
        return redirect(url_for('prode_bp.index'))

    grupos = {}
    for equipo in torneo.equipos:
        if not equipo.grupo or equipo.nombre.startswith('Por definir'):
            continue
        if equipo.grupo not in grupos:
            grupos[equipo.grupo] = {}
        grupos[equipo.grupo][equipo.id] = {
            'equipo': equipo,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
            'gf': 0, 'gc': 0, 'dif': 0, 'pts': 0,
        }

    for fase in torneo.fases:
        if fase.orden != 0 and 'grupo' not in fase.nombre.lower():
            continue
        for partido in fase.partidos:
            if partido.estado != 'cerrado':
                continue
            if partido.goles_local is None or partido.goles_visitante is None:
                continue
            lid = partido.equipo_local_id
            vid = partido.equipo_visitante_id
            gl  = partido.goles_local
            gv  = partido.goles_visitante
            for grupo_data in grupos.values():
                if lid in grupo_data:
                    grupo_data[lid]['pj'] += 1
                    grupo_data[lid]['gf'] += gl
                    grupo_data[lid]['gc'] += gv
                    if gl > gv:   grupo_data[lid]['pg'] += 1; grupo_data[lid]['pts'] += 3
                    elif gl == gv: grupo_data[lid]['pe'] += 1; grupo_data[lid]['pts'] += 1
                    else:          grupo_data[lid]['pp'] += 1
                if vid in grupo_data:
                    grupo_data[vid]['pj'] += 1
                    grupo_data[vid]['gf'] += gv
                    grupo_data[vid]['gc'] += gl
                    if gv > gl:   grupo_data[vid]['pg'] += 1; grupo_data[vid]['pts'] += 3
                    elif gv == gl: grupo_data[vid]['pe'] += 1; grupo_data[vid]['pts'] += 1
                    else:          grupo_data[vid]['pp'] += 1

    grupos_ordenados = {}
    for nombre_grupo in sorted(grupos.keys()):
        filas = list(grupos[nombre_grupo].values())
        for f in filas:
            f['dif'] = f['gf'] - f['gc']
        filas.sort(key=lambda x: (-x['pts'], -x['dif'], -x['gf']))
        grupos_ordenados[nombre_grupo] = filas

    return render_template('prode/grupos/index.html',
                           titulo=f'Tabla de grupos — {torneo.nombre}',
                           torneo=torneo,
                           grupos=grupos_ordenados)


@prode_bp.route('/admin/torneos')
@login_required
@requiere_funcion()
def admin_torneos():
    torneos = ProdeTorneo.query.order_by(ProdeTorneo.fecha_inicio.desc()).all()
    return render_template('prode/admin/torneos.html',
                           titulo='Admin — Torneos', torneos=torneos)


@prode_bp.route('/admin/torneos/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_torneo_nuevo():
    if request.method == 'POST':
        t = _torneo_desde_form(ProdeTorneo())
        # Crear config de puntaje con valores por defecto
        config = ProdeConfigPuntaje(
            resultado_exacto  = int(request.form.get('pts_exacto',  3)),
            resultado_parcial = int(request.form.get('pts_parcial', 1)),
            resultado_errado  = int(request.form.get('pts_errado',  0)),
        )
        t.config = config
        db.session.add(t)
        db.session.commit()
        flash(f'Torneo <strong>{t.nombre}</strong> creado.', 'success')
        return redirect(url_for('prode_bp.admin_torneos'))
    return render_template('prode/admin/torneo_form.html',
                           titulo='Nuevo torneo', torneo=None)


@prode_bp.route('/admin/torneos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_torneo_editar(id):
    torneo = ProdeTorneo.query.get_or_404(id)
    if request.method == 'POST':
        _torneo_desde_form(torneo)
        if torneo.config:
            torneo.config.resultado_exacto  = int(request.form.get('pts_exacto',  3))
            torneo.config.resultado_parcial = int(request.form.get('pts_parcial', 1))
            torneo.config.resultado_errado  = int(request.form.get('pts_errado',  0))
        db.session.commit()
        flash(f'Torneo <strong>{torneo.nombre}</strong> actualizado.', 'success')
        return redirect(url_for('prode_bp.admin_torneos'))
    return render_template('prode/admin/torneo_form.html',
                           titulo='Editar torneo', torneo=torneo)


@prode_bp.route('/admin/torneos/<int:id>/activar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_torneo_activar(id):
    torneo = ProdeTorneo.query.get_or_404(id)
    torneo.activo = not torneo.activo
    db.session.commit()
    flash(f'Torneo {("activado" if torneo.activo else "desactivado")}.', 'success')
    return redirect(url_for('prode_bp.admin_torneos'))


def _torneo_desde_form(t):
    f = request.form

    def parse_date(val):
        if not val:
            return None
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None

    t.nombre               = f.get('nombre', '').strip()
    t.descripcion          = f.get('descripcion', '').strip() or None
    t.fecha_inicio         = parse_date(f.get('fecha_inicio'))
    t.fecha_fin            = parse_date(f.get('fecha_fin'))
    t.inscripcion_abierta  = f.get('inscripcion_abierta') == '1'
    try:
        t.precio_inscripcion = float(f.get('precio_inscripcion') or 0)
    except ValueError:
        t.precio_inscripcion = 0
    return t


# =================================================================
# ADMIN — FASES
# =================================================================

@prode_bp.route('/admin/torneos/<int:id>/eliminar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_torneo_eliminar(id):
    torneo = ProdeTorneo.query.get_or_404(id)
    nombre = torneo.nombre
    try:
        db.session.delete(torneo)
        db.session.commit()
        flash(f'Torneo <strong>{nombre}</strong> eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('No se pudo eliminar el torneo.', 'danger')
    return redirect(url_for('prode_bp.admin_torneos'))


@prode_bp.route('/admin/torneos/<int:torneo_id>/fases/nueva', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_fase_nueva(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)
    if request.method == 'POST':
        fase = ProdeFase(
            torneo_id = torneo_id,
            nombre    = request.form.get('nombre', '').strip(),
            orden     = int(request.form.get('orden', 0)),
        )
        db.session.add(fase)
        db.session.commit()
        flash(f'Fase <strong>{fase.nombre}</strong> creada.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo_id))
    return render_template('prode/admin/fase_form.html',
                           titulo='Nueva fase', torneo=torneo, fase=None)


@prode_bp.route('/admin/fases/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_fase_editar(id):
    fase = ProdeFase.query.get_or_404(id)
    if request.method == 'POST':
        fase.nombre = request.form.get('nombre', '').strip()
        fase.orden  = int(request.form.get('orden', 0))
        db.session.commit()
        flash('Fase actualizada.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=fase.torneo_id))
    return render_template('prode/admin/fase_form.html',
                           titulo='Editar fase', torneo=fase.torneo, fase=fase)


@prode_bp.route('/admin/fases/<int:id>/eliminar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_fase_eliminar(id):
    fase = ProdeFase.query.get_or_404(id)
    torneo_id = fase.torneo_id
    if fase.partidos:
        flash('No se puede eliminar una fase con partidos cargados.', 'danger')
    else:
        db.session.delete(fase)
        db.session.commit()
        flash('Fase eliminada.', 'success')
    return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo_id))


# =================================================================
# ADMIN — EQUIPOS
# =================================================================

@prode_bp.route('/admin/torneos/<int:torneo_id>/equipos/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_equipo_nuevo(torneo_id):
    torneo = ProdeTorneo.query.get_or_404(torneo_id)
    if request.method == 'POST':
        raw_escudo = request.form.get('escudo_url', '').strip()
        if '/static/' in raw_escudo:
            raw_escudo = raw_escudo.split('/static/', 1)[1]
        e = ProdeEquipo(
            torneo_id  = torneo_id,
            nombre     = request.form.get('nombre', '').strip(),
            grupo      = request.form.get('grupo', '').strip().upper() or None,
            escudo_url = raw_escudo or None,
            codigo_iso = request.form.get('codigo_iso', '').strip().lower() or None,
        )
        db.session.add(e)
        db.session.commit()
        flash(f'Equipo <strong>{e.nombre}</strong> agregado.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo_id))
    return render_template('prode/admin/equipo_form.html',
                           titulo='Nuevo equipo', torneo=torneo, equipo=None)


@prode_bp.route('/admin/equipos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_equipo_editar(id):
    equipo = ProdeEquipo.query.get_or_404(id)
    if request.method == 'POST':
        equipo.nombre     = request.form.get('nombre', '').strip()
        equipo.grupo      = request.form.get('grupo', '').strip().upper() or None
        raw_escudo = request.form.get('escudo_url', '').strip()
        if '/static/' in raw_escudo:
            raw_escudo = raw_escudo.split('/static/', 1)[1]
        equipo.escudo_url = raw_escudo or None
        equipo.codigo_iso = request.form.get('codigo_iso', '').strip().lower() or None
        db.session.commit()
        flash('Equipo actualizado.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=equipo.torneo_id))
    return render_template('prode/admin/equipo_form.html',
                           titulo='Editar equipo', torneo=equipo.torneo, equipo=equipo)


@prode_bp.route('/admin/equipos/<int:id>/eliminar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_equipo_eliminar(id):
    equipo = ProdeEquipo.query.get_or_404(id)
    torneo_id = equipo.torneo_id
    try:
        db.session.delete(equipo)
        db.session.commit()
        flash('Equipo eliminado.', 'success')
    except Exception:
        db.session.rollback()
        flash('No se puede eliminar — el equipo tiene partidos asociados.', 'danger')
    return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo_id))


# =================================================================
# ADMIN — PARTIDOS
# =================================================================

@prode_bp.route('/admin/fases/<int:fase_id>/partidos/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_partido_nuevo(fase_id):
    fase   = ProdeFase.query.get_or_404(fase_id)
    torneo = fase.torneo
    equipos = ProdeEquipo.query.filter_by(torneo_id=torneo.id)\
                               .order_by(ProdeEquipo.grupo, ProdeEquipo.nombre).all()
    if request.method == 'POST':
        partido = _partido_desde_form(ProdePartido(), fase_id)
        db.session.add(partido)
        db.session.commit()
        flash('Partido agregado.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo.id))
    return render_template('prode/admin/partido_form.html',
                           titulo='Nuevo partido', fase=fase,
                           torneo=torneo, equipos=equipos, partido=None)


@prode_bp.route('/admin/partidos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_funcion()
def admin_partido_editar(id):
    partido = ProdePartido.query.get_or_404(id)
    torneo  = partido.fase.torneo
    equipos = ProdeEquipo.query.filter_by(torneo_id=torneo.id)\
                               .order_by(ProdeEquipo.grupo, ProdeEquipo.nombre).all()

    if request.method == 'POST':
        # Partido cerrado: solo se permite editar fecha/equipos, no el resultado
        # (el resultado se corrige desde el botón de cerrar/corregir)
        if partido.estado == 'cerrado':
            flash('Para corregir el resultado usá el botón "Corregir resultado".', 'warning')
            return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo.id))
        _partido_desde_form(partido, partido.fase_id)
        db.session.commit()
        flash('Partido actualizado.', 'success')
        return redirect(url_for('prode_bp.admin_torneo_editar', id=torneo.id))

    return render_template('prode/admin/partido_form.html',
                           titulo='Editar partido', fase=partido.fase,
                           torneo=torneo, equipos=equipos, partido=partido)


@prode_bp.route('/admin/partidos/<int:id>/cerrar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_partido_cerrar(id):
    partido = ProdePartido.query.get_or_404(id)

    gl = request.form.get('goles_local', '').strip()
    gv = request.form.get('goles_visitante', '').strip()

    if not gl.isdigit() or not gv.isdigit():
        flash('Ingresá el resultado antes de cerrar.', 'danger')
        return redirect(url_for('prode_bp.admin_torneo_editar',
                                id=partido.fase.torneo_id))

    es_correccion = partido.estado == 'cerrado'

    partido.goles_local     = int(gl)
    partido.goles_visitante = int(gv)
    partido.estado          = 'cerrado'

    # Recalcular puntos para TODOS los pronósticos
    for pron in partido.pronosticos:
        pron.puntos = calcular_puntos(partido, pron)

    db.session.commit()

    if es_correccion:
        flash(f'Resultado corregido: '
              f'{partido.goles_local}–{partido.goles_visitante}. '
              f'Puntos recalculados para todos los participantes.', 'success')
    else:
        # Notificaciones por mail solo al cerrar por primera vez
        try:
            from app.services.prode_mail import notificar_cierre_partido
            notificar_cierre_partido(partido)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Prode mail error: {e}')
        flash(f'Partido cerrado. Resultado: '
              f'{partido.goles_local}–{partido.goles_visitante}. '
              f'Puntos calculados.', 'success')

    return redirect(url_for('prode_bp.admin_torneo_editar',
                            id=partido.fase.torneo_id))


def _partido_desde_form(p, fase_id):
    f = request.form
    p.fase_id             = fase_id
    p.equipo_local_id     = int(f.get('equipo_local_id'))
    p.equipo_visitante_id = int(f.get('equipo_visitante_id'))
    p.fecha_hora          = f.get('fecha_hora')
    p.goles_local         = int(f['goles_local'])   if f.get('goles_local')     else None
    p.goles_visitante     = int(f['goles_visitante']) if f.get('goles_visitante') else None
    # Estado: solo pendiente (jugando eliminado — no hay tiempo real)
    if p.estado != 'cerrado':
        p.estado = 'pendiente'
    return p


# =================================================================
# ADMIN — INSCRIPCIONES
# =================================================================

@prode_bp.route('/admin/inscripciones')
@login_required
@requiere_funcion()
def admin_inscripciones():
    torneo_id = request.args.get('torneo_id', type=int)
    q = ProdeInscripcion.query
    if torneo_id:
        q = q.filter_by(torneo_id=torneo_id)

    inscripciones = q.order_by(
        ProdeInscripcion.estado,
        ProdeInscripcion.created_at
    ).all()

    torneos = ProdeTorneo.query.order_by(ProdeTorneo.fecha_inicio.desc()).all()

    # ── Resumen financiero ─────────────────────────────────────────────────
    resumen = {
        'aprobado':      0,
        'pendiente':     0,
        'pago_pendiente':0,
        'rechazado':     0,
        'recaudado':     0.0,
    }
    for insc in inscripciones:
        estado = insc.estado
        if estado in resumen:
            resumen[estado] += 1
        precio = float(insc.torneo.precio_inscripcion or 0)
        if estado == 'aprobado' and precio > 0:
            resumen['recaudado'] += precio

    return render_template('prode/admin/inscripciones.html',
                           titulo='Admin — Inscripciones',
                           inscripciones=inscripciones,
                           torneos=torneos,
                           torneo_id_sel=torneo_id,
                           resumen=resumen)


@prode_bp.route('/admin/inscripciones/<int:id>/aprobar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_inscripcion_aprobar(id):
    insc = ProdeInscripcion.query.get_or_404(id)
    insc.estado = 'aprobado'
    db.session.commit()
    flash(f'Inscripción de <strong>{insc.usuario.nombre_completo}</strong> aprobada.', 'success')
    return redirect(url_for('prode_bp.admin_inscripciones',
                            torneo_id=insc.torneo_id))


@prode_bp.route('/admin/inscripciones/<int:id>/rechazar', methods=['POST'])
@login_required
@requiere_funcion()
def admin_inscripcion_rechazar(id):
    insc = ProdeInscripcion.query.get_or_404(id)
    insc.estado = 'rechazado'
    db.session.commit()
    flash(f'Inscripción de <strong>{insc.usuario.nombre_completo}</strong> rechazada.', 'warning')
    return redirect(url_for('prode_bp.admin_inscripciones',
                            torneo_id=insc.torneo_id))