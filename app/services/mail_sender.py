# app/services/mail_sender.py
#
# Abstracción de envío de email con dos backends:
#
#   MAIL_BACKEND=resend  → API HTTPS de Resend (funciona en Render free tier)
#   MAIL_BACKEND=smtp    → Flask-Mail por SMTP (para servidores propios o pagos)
#
# Uso:
#   from app.services.mail_sender import enviar_async
#   enviar_async(app, subject='...', recipients=['a@b.com'], html='<p>...</p>')
#
# El envío siempre es asíncrono (thread daemon) para no bloquear el worker.

import logging
import threading
import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)


def enviar_async(app, subject: str, recipients: list[str], html: str):
    """
    Despacha el mail en un thread daemon.
    El worker de gunicorn no se bloquea; si falla queda en el log.
    """
    def _run():
        with app.app_context():
            backend = app.config.get('MAIL_BACKEND', 'resend').lower()
            if backend == 'smtp':
                _enviar_smtp(app, subject, recipients, html)
            else:
                _enviar_resend(app, subject, recipients, html)

    threading.Thread(target=_run, daemon=True).start()


# ── Backend Resend ────────────────────────────────────────────────────────────

def _enviar_resend(app, subject, recipients, html):
    api_key = app.config.get('RESEND_API_KEY', '').strip()
    sender  = app.config.get('MAIL_DEFAULT_SENDER', 'noreply@prode.app')

    if not api_key:
        app.logger.warning('Mail Resend: RESEND_API_KEY no configurada — mail no enviado.')
        return

    payload = json.dumps({
        'from':    sender,
        'to':      recipients,
        'subject': subject,
        'html':    html,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data    = payload,
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        },
        method = 'POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            app.logger.warning('Mail Resend OK: "%s" → %s  [%s]', subject, recipients, resp.status)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        app.logger.warning('Mail Resend HTTP %s: "%s" → %s — %s', e.code, subject, recipients, body)
    except Exception as e:
        app.logger.warning('Mail Resend ERROR: "%s" → %s — %s', subject, recipients, e)


# ── Backend SMTP (Flask-Mail) ─────────────────────────────────────────────────

def _enviar_smtp(app, subject, recipients, html):
    try:
        from flask_mail import Mail, Message
        mail = Mail(app)
        msg  = Message(subject=subject, recipients=recipients, html=html)
        mail.send(msg)
        app.logger.warning('Mail SMTP OK: "%s" → %s', subject, recipients)
    except Exception as e:
        app.logger.warning('Mail SMTP ERROR: "%s" → %s — %s', subject, recipients, e)
