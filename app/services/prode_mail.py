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
import threading

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


TEMPLATE_BIENVENIDA = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

  <div style="background:#003263; padding:20px; text-align:center;">
    <h2 style="color:#fff; margin:0;">🏆 Bienvenido/a al Prode</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola <strong>{{ nombre }}</strong>,</p>

    <p>Tu cuenta fue creada exitosamente. Ya podés explorar los torneos disponibles
       y empezar a hacer tus pronósticos.</p>

    <p style="margin-top:24px;">
      <a href="{{ url_inicio }}"
         style="background:#003263; color:#fff; padding:10px 20px;
                border-radius:6px; text-decoration:none; font-weight:bold;">
        Ir al Prode
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


def enviar_bienvenida(usuario):
    """
    Envía mail de bienvenida al usuario recién registrado.
    Falla silenciosamente si Flask-Mail no está configurado.
    """
    mail = _get_mail()
    if not mail:
        return

    if not usuario.email:
        return

    from flask import url_for
    try:
        url_inicio = url_for('main_bp.index', _external=True)
    except Exception:
        url_inicio = '#'

    html = render_template_string(
        TEMPLATE_BIENVENIDA,
        nombre     = usuario.nombre,
        url_inicio = url_inicio,
    )

    app = current_app._get_current_object()
    _enviar_en_thread(app, '¡Bienvenido/a al Prode!', [usuario.email], html)


TEMPLATE_INSCRIPCION_PENDIENTE_ADMIN = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

  <div style="background:#003263; padding:20px; text-align:center;">
    <h2 style="color:#fff; margin:0;">🏆 Nueva solicitud de inscripción</h2>
  </div>

  <div style="padding:24px;">
    <p>Se recibió una nueva solicitud de inscripción al torneo
       <strong>{{ torneo }}</strong>.</p>

    <table style="width:100%; border-collapse:collapse; margin:16px 0;">
      <tr>
        <td style="padding:8px; border-bottom:1px solid #e5e7eb; color:#666; width:40%;">Jugador</td>
        <td style="padding:8px; border-bottom:1px solid #e5e7eb;"><strong>{{ nombre_completo }}</strong></td>
      </tr>
      <tr>
        <td style="padding:8px; border-bottom:1px solid #e5e7eb; color:#666;">Email</td>
        <td style="padding:8px; border-bottom:1px solid #e5e7eb;">{{ email }}</td>
      </tr>
      <tr>
        <td style="padding:8px; color:#666;">Torneo</td>
        <td style="padding:8px;">{{ torneo }}</td>
      </tr>
    </table>

    <p style="margin-top:24px;">
      <a href="{{ url_inscripciones }}"
         style="background:#003263; color:#fff; padding:10px 20px;
                border-radius:6px; text-decoration:none; font-weight:bold;">
        Gestionar inscripciones
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

TEMPLATE_INSCRIPCION_APROBADA = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

  <div style="background:#003263; padding:20px; text-align:center;">
    <h2 style="color:#fff; margin:0;">🏆 ¡Inscripción aprobada!</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola <strong>{{ nombre }}</strong>,</p>

    <p>Tu inscripción al torneo <strong>{{ torneo }}</strong> fue
       <span style="color:#16a34a; font-weight:700;">aprobada</span>.
       Ya podés ingresar y hacer tus pronósticos.</p>

    <p style="margin-top:24px;">
      <a href="{{ url_pronosticos }}"
         style="background:#003263; color:#fff; padding:10px 20px;
                border-radius:6px; text-decoration:none; font-weight:bold;">
        Ir a pronosticar
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


def _get_mail():
    """Devuelve instancia de Mail o None si no está configurado."""
    try:
        from flask_mail import Mail
        return Mail(current_app)
    except Exception as e:
        logger.warning(f'Prode mail: Flask-Mail no disponible — {e}')
        return None


def _enviar_en_thread(app, subject, recipients, html):
    """Envía un mail en thread separado para no bloquear el worker de gunicorn."""
    def _run():
        with app.app_context():
            try:
                from flask_mail import Mail, Message
                mail = Mail(app)
                msg  = Message(subject=subject, recipients=recipients, html=html)
                mail.send(msg)
                app.logger.warning('Prode mail OK: "%s" → %s', subject, recipients)
            except Exception as e:
                app.logger.warning('Prode mail ERROR: "%s" → %s — %s', subject, recipients, e)

    threading.Thread(target=_run, daemon=True).start()


def notificar_inscripcion_pendiente(insc):
    """
    Avisa a todos los administradores que hay una nueva inscripción pendiente.
    """
    mail = _get_mail()
    if not mail:
        return

    from flask import url_for
    from app.models.usuario import Usuario
    from app.models.rol import Rol

    admins = (
        Usuario.query
        .join(Usuario.roles)
        .filter(Rol.nombre == 'Prode - Admin', Usuario.email.isnot(None))
        .all()
    )
    if not admins:
        logger.warning('Prode mail: no se encontraron administradores para notificar.')
        return

    try:
        url_inscripciones = url_for(
            'prode_bp.admin_inscripciones',
            torneo_id=insc.torneo_id,
            _external=True,
        )
    except Exception:
        url_inscripciones = '#'

    html = render_template_string(
        TEMPLATE_INSCRIPCION_PENDIENTE_ADMIN,
        nombre_completo  = insc.usuario.nombre_completo,
        email            = insc.usuario.email or '—',
        torneo           = insc.torneo.nombre,
        url_inscripciones = url_inscripciones,
    )

    destinatarios = [a.email for a in admins]
    app = current_app._get_current_object()
    _enviar_en_thread(app, f'[Prode] Nueva inscripción — {insc.torneo.nombre}', destinatarios, html)


def notificar_inscripcion_aprobada(insc):
    """
    Avisa al jugador que su inscripción fue aprobada y ya puede pronosticar.
    """
    mail = _get_mail()
    if not mail:
        return

    if not insc.usuario.email:
        return

    from flask import url_for
    try:
        url_pronosticos = url_for(
            'prode_bp.pronosticos',
            torneo_id=insc.torneo_id,
            _external=True,
        )
    except Exception:
        url_pronosticos = '#'

    html = render_template_string(
        TEMPLATE_INSCRIPCION_APROBADA,
        nombre          = insc.usuario.nombre,
        torneo          = insc.torneo.nombre,
        url_pronosticos = url_pronosticos,
    )

    app = current_app._get_current_object()
    _enviar_en_thread(
        app,
        f'[Prode] ¡Inscripción aprobada! — {insc.torneo.nombre}',
        [insc.usuario.email],
        html,
    )


def notificar_cierre_partido(partido):
    """
    Envía mail a cada jugador inscripto y aprobado del torneo
    informando el resultado y sus puntos.
    Se ejecuta en un thread para no bloquear el worker de gunicorn.
    """
    app      = current_app._get_current_object()
    partido_id = partido.id

    def _run():
        with app.app_context():
            try:
                from flask_mail import Mail, Message
                mail = Mail(app)
            except Exception as e:
                app.logger.warning(f'Prode mail: Flask-Mail no disponible — {e}')
                return

            from flask import url_for
            from app.models.prode import ProdeInscripcion, ProdePronostico, ProdePartido

            partido_local = ProdePartido.query.get(partido_id)
            if not partido_local:
                return

            torneo  = partido_local.fase.torneo
            config  = torneo.config
            pts_exacto  = config.resultado_exacto  if config else 3
            pts_parcial = config.resultado_parcial if config else 1

            try:
                url_ranking = url_for('prode_bp.ranking_torneo',
                                      torneo_id=torneo.id, _external=True)
            except Exception:
                url_ranking = '#'

            inscriptos = ProdeInscripcion.query.filter_by(
                torneo_id=torneo.id, estado='aprobado'
            ).all()

            enviados = 0
            for insc in inscriptos:
                usuario = insc.usuario
                if not usuario.email:
                    continue

                pron = ProdePronostico.query.filter_by(
                    usuario_id=usuario.id,
                    partido_id=partido_id,
                ).first()

                html = render_template_string(
                    TEMPLATE_RESULTADO,
                    nombre         = usuario.nombre,
                    local          = partido_local.equipo_local.nombre,
                    visitante      = partido_local.equipo_visitante.nombre,
                    torneo         = torneo.nombre,
                    fase           = partido_local.fase.nombre,
                    gl             = partido_local.goles_local,
                    gv             = partido_local.goles_visitante,
                    pron_local     = pron.goles_local      if pron else None,
                    pron_visitante = pron.goles_visitante  if pron else None,
                    puntos         = pron.puntos           if pron else 0,
                    pts_exacto     = pts_exacto,
                    pts_parcial    = pts_parcial,
                    url_ranking    = url_ranking,
                )
                try:
                    subject = (
                        f'[Prode] {partido_local.equipo_local.nombre} '
                        f'{partido_local.goles_local}–{partido_local.goles_visitante} '
                        f'{partido_local.equipo_visitante.nombre}'
                    )
                    msg = Message(subject=subject, recipients=[usuario.email], html=html)
                    mail.send(msg)
                    enviados += 1
                except Exception as e:
                    app.logger.warning(f'Prode mail: error enviando a {usuario.email} — {e}')

            app.logger.warning('Prode mail: %d mails enviados para partido %d', enviados, partido_id)

    threading.Thread(target=_run, daemon=True).start()
