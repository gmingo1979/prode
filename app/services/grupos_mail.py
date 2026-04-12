# app/services/grupos_mail.py
#
# Notificaciones de email para grupos privados del Prode.
# El backend (Resend o SMTP) se configura con MAIL_BACKEND en .env

import logging

from flask import current_app, render_template_string, url_for
from app.services.mail_sender import enviar_async

logger = logging.getLogger(__name__)


def _enviar(subject, recipients, html):
    app = current_app._get_current_object()
    enviar_async(app, subject=subject, recipients=recipients, html=html)


# ── Templates ────────────────────────────────────────────────────────────────

_TMPL_INVITACION = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">

  <div style="background:#003263;padding:20px;text-align:center;">
    <h2 style="color:#fff;margin:0;">🏆 Te invitaron a un grupo del Prode</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola! <strong>{{ invitado_por }}</strong> te invitó a unirte al grupo
       <strong>{{ grupo }}</strong> en el Prode.</p>

    {% if descripcion %}
    <p style="color:#555;font-style:italic;">"{{ descripcion }}"</p>
    {% endif %}

    <p>Hacé click en el botón para aceptar la invitación:</p>

    <p style="text-align:center;margin:28px 0;">
      <a href="{{ url_aceptar }}"
         style="background:#003263;color:#fff;padding:12px 28px;
                border-radius:6px;text-decoration:none;font-weight:bold;font-size:1rem;">
        Unirme al grupo
      </a>
    </p>

    <p style="color:#888;font-size:0.85rem;">
      También podés ingresar al Prode y usar el código
      <strong style="font-family:monospace;font-size:1rem;letter-spacing:0.1em;">{{ codigo }}</strong>
      en "Unirme con código".
    </p>

    {% if es_nuevo_usuario %}
    <hr style="border:none;border-top:1px solid #e5e9f0;margin:20px 0;">
    <p style="font-size:0.85rem;color:#555;">
      ¿Todavía no tenés cuenta? Podés crear una gratis haciendo click en el botón
      — el sistema te va a pedir que te registres y después te va a unir al grupo automáticamente.
    </p>
    {% endif %}
  </div>

  <div style="background:#f0f2f5;padding:12px;text-align:center;font-size:0.75rem;color:#888;">
    Prode Deportivo
  </div>
</body>
</html>
"""

_TMPL_NUEVO_MIEMBRO = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">

  <div style="background:#003263;padding:20px;text-align:center;">
    <h2 style="color:#fff;margin:0;">🏆 Nuevo miembro en tu grupo</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola <strong>{{ creador }}</strong>,</p>
    <p><strong>{{ nuevo_miembro }}</strong> acaba de unirse a tu grupo
       <strong>{{ grupo }}</strong>.</p>
    <p>El grupo ya cuenta con <strong>{{ cantidad }} miembro{{ 's' if cantidad != 1 }}</strong>.</p>

    <p style="margin-top:24px;">
      <a href="{{ url_grupo }}"
         style="background:#003263;color:#fff;padding:10px 20px;
                border-radius:6px;text-decoration:none;font-weight:bold;">
        Ver el grupo
      </a>
    </p>
  </div>

  <div style="background:#f0f2f5;padding:12px;text-align:center;font-size:0.75rem;color:#888;">
    Prode Deportivo
  </div>
</body>
</html>
"""

_TMPL_EXPULSADO = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">

  <div style="background:#7c0a1a;padding:20px;text-align:center;">
    <h2 style="color:#fff;margin:0;">🏆 Fuiste removido de un grupo</h2>
  </div>

  <div style="padding:24px;">
    <p>Hola <strong>{{ miembro }}</strong>,</p>
    <p>El administrador del grupo te removió de <strong>{{ grupo }}</strong>.</p>
    <p>Podés unirte a otro grupo o crear el tuyo propio desde el Prode.</p>

    <p style="margin-top:24px;">
      <a href="{{ url_grupos }}"
         style="background:#003263;color:#fff;padding:10px 20px;
                border-radius:6px;text-decoration:none;font-weight:bold;">
        Ir a mis grupos
      </a>
    </p>
  </div>

  <div style="background:#f0f2f5;padding:12px;text-align:center;font-size:0.75rem;color:#888;">
    Prode Deportivo
  </div>
</body>
</html>
"""


# ── Funciones públicas ────────────────────────────────────────────────────────

def enviar_invitacion(invitacion, es_nuevo_usuario: bool = False):
    """Envía el mail de invitación al email destino."""
    try:
        url_aceptar = url_for(
            'grupos_bp.aceptar_invitacion',
            token=invitacion.token,
            _external=True,
        )
    except Exception:
        url_aceptar = '#'

    html = render_template_string(
        _TMPL_INVITACION,
        invitado_por     = invitacion.invitado_por.nombre_completo,
        grupo            = invitacion.grupo.nombre,
        descripcion      = invitacion.grupo.descripcion,
        codigo           = invitacion.grupo.codigo,
        url_aceptar      = url_aceptar,
        es_nuevo_usuario = es_nuevo_usuario,
    )
    _enviar(
        subject    = f'[Prode] {invitacion.invitado_por.nombre} te invitó al grupo "{invitacion.grupo.nombre}"',
        recipients = [invitacion.email],
        html       = html,
    )


def notificar_nuevo_miembro(grupo, nuevo_usuario):
    """Avisa al creador del grupo que alguien se unió."""
    creador = grupo.creador
    if not creador.email or creador.id == nuevo_usuario.id:
        return

    try:
        url_grupo = url_for('grupos_bp.detalle', grupo_id=grupo.id, _external=True)
    except Exception:
        url_grupo = '#'

    html = render_template_string(
        _TMPL_NUEVO_MIEMBRO,
        creador       = creador.nombre,
        nuevo_miembro = nuevo_usuario.nombre_completo,
        grupo         = grupo.nombre,
        cantidad      = grupo.cantidad_miembros(),
        url_grupo     = url_grupo,
    )
    _enviar(
        subject    = f'[Prode] {nuevo_usuario.nombre} se unió a tu grupo "{grupo.nombre}"',
        recipients = [creador.email],
        html       = html,
    )


def notificar_expulsion(grupo, usuario_removido):
    """Avisa al usuario que fue removido del grupo."""
    if not usuario_removido.email:
        return

    try:
        url_grupos = url_for('grupos_bp.mis_grupos', _external=True)
    except Exception:
        url_grupos = '#'

    html = render_template_string(
        _TMPL_EXPULSADO,
        miembro    = usuario_removido.nombre,
        grupo      = grupo.nombre,
        url_grupos = url_grupos,
    )
    _enviar(
        subject    = f'[Prode] Fuiste removido del grupo "{grupo.nombre}"',
        recipients = [usuario_removido.email],
        html       = html,
    )
