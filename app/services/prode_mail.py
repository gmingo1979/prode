# app/services/prode_mail.py
#
# Notificaciones por mail del Prode.
# Se envían al cerrar un partido desde prode_partidos_cerrar().
#
# Configuración requerida en .env / config.py:
#   MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD
#   MAIL_DEFAULT_SENDER
#
# Usa Flask-Mail. Si no está configurado, falla silenciosamente y loggea.

import logging
from flask import current_app, render_template_string

logger = logging.getLogger(__name__)

# Template del mail — HTML inline para máxima compatibilidad de clientes de correo
TEMPLATE_RESULTADO = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

  <div style="background:#003263; padding:20px; text-align:center;">
    <h2 style="color:#fff; margin:0;">🏆 Prode — Resultado del partido</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola <strong>{{ nombre }}</strong>,</p>

    <p>El partido <strong>{{ local }} vs {{ visitante }}</strong>
       de <em>{{ torneo }}</em> ({{ fase }}) ya tiene resultado:</p>

    <div style="text-align:center; font-size:2.5rem; font-weight:700;
                padding:20px; background:#f8fafc; border-radius:8px; margin:20px 0;">
      {{ local }} <span style="color:#003263;">{{ gl }} – {{ gv }}</span> {{ visitante }}
    </div>

    {% if pron_local is not none %}
    <p>Tu pronóstico fue: <strong>{{ pron_local }} – {{ pron_visitante }}</strong></p>

    {% if puntos == pts_exacto %}
    <p style="color:#16a34a; font-weight:700; font-size:1.1rem;">
      🎯 ¡Resultado exacto! Sumaste <strong>{{ puntos }} puntos</strong>.
    </p>
    {% elif puntos == pts_parcial %}
    <p style="color:#f59e0b; font-weight:700;">
      ✅ Acertaste el resultado. Sumaste <strong>{{ puntos }} punto{{ 's' if puntos != 1 }}</strong>.
    </p>
    {% else %}
    <p style="color:#dc2626;">
      ❌ No acertaste esta vez. Sumaste <strong>0 puntos</strong>.
    </p>
    {% endif %}

    {% else %}
    <p style="color:#888;">No realizaste un pronóstico para este partido.</p>
    {% endif %}

    <p style="margin-top:24px;">
      <a href="{{ url_ranking }}"
         style="background:#003263; color:#fff; padding:10px 20px;
                border-radius:6px; text-decoration:none; font-weight:bold;">
        Ver ranking completo
      </a>
    </p>

  </div>

  <div style="background:#f0f2f5; padding:12px; text-align:center;
              font-size:0.75rem; color:#888;">
    Prode
  </div>

</body>
</html>
"""


def notificar_cierre_partido(partido):
    """
    Envía mail a cada jugador inscripto y aprobado del torneo
    informando el resultado y sus puntos.

    Falla silenciosamente si Flask-Mail no está configurado.
    """
    try:
        from flask_mail import Mail, Message
        mail = Mail(current_app)
    except Exception as e:
        logger.warning(f'Prode mail: Flask-Mail no disponible — {e}')
        return

    from flask import url_for
    from app.models.prode import ProdeInscripcion, ProdePronostico

    torneo  = partido.fase.torneo
    config  = torneo.config
    pts_exacto  = config.resultado_exacto  if config else 3
    pts_parcial = config.resultado_parcial if config else 1

    try:
        url_ranking = url_for('prode_bp.ranking_torneo',
                              torneo_id=torneo.id, _external=True)
    except Exception:
        url_ranking = '#'

    inscriptos = ProdeInscripcion.query.filter_by(
        torneo_id=torneo.id,
        estado='aprobado'
    ).all()

    enviados = 0
    for insc in inscriptos:
        usuario = insc.usuario
        if not usuario.email:
            continue

        pron = ProdePronostico.query.filter_by(
            usuario_id=usuario.id,
            partido_id=partido.id,
        ).first()

        html = render_template_string(
            TEMPLATE_RESULTADO,
            nombre         = usuario.nombre,
            local          = partido.equipo_local.nombre,
            visitante      = partido.equipo_visitante.nombre,
            torneo         = torneo.nombre,
            fase           = partido.fase.nombre,
            gl             = partido.goles_local,
            gv             = partido.goles_visitante,
            pron_local     = pron.goles_local      if pron else None,
            pron_visitante = pron.goles_visitante  if pron else None,
            puntos         = pron.puntos           if pron else 0,
            pts_exacto     = pts_exacto,
            pts_parcial    = pts_parcial,
            url_ranking    = url_ranking,
        )

        try:
            msg = Message(
                subject = f'[Prode] {partido.equipo_local.nombre} {partido.goles_local}–{partido.goles_visitante} {partido.equipo_visitante.nombre}',
                recipients = [usuario.email],
                html       = html,
            )
            mail.send(msg)
            enviados += 1
        except Exception as e:
            logger.warning(f'Prode mail: error enviando a {usuario.email} — {e}')

    logger.info(f'Prode mail: {enviados} mails enviados para partido {partido.id}')
