# -*- coding: utf-8 -*-
# app/routes/pwa.py
#
# Rutas necesarias para la PWA.
# Registrar en __init__.py:
#   from app.routes.pwa import pwa_bp
#   flask_app.register_blueprint(pwa_bp)

from flask import Blueprint, jsonify, render_template, send_from_directory
import os

pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.route("/health")
def health():
    """
    Healthcheck para monitoreo externo (UptimeRobot, cron-job.org, etc.).
    Responde 200 con un JSON mínimo. No requiere autenticación.
    También sirve para mantener activo el servidor en Render free tier.
    """
    from datetime import datetime, timezone
    return jsonify(status='ok', ts=datetime.now(timezone.utc).isoformat()), 200


@pwa_bp.route("/offline")
def offline():
    """Página que muestra el Service Worker cuando no hay red."""
    return render_template("pwa/offline.html")


@pwa_bp.route("/static/manifest.json")
def manifest():
    """Sirve el manifest.json desde static/."""
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    return send_from_directory(os.path.abspath(static_dir), 'manifest.json',
                               mimetype='application/manifest+json')