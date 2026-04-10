# app/routes/main.py
#
# Rutas principales: inicio, logout.

from flask import Blueprint, redirect, session, url_for
from flask_login import current_user, login_required

main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
@login_required
def index():
    """Redirige al hub del Prode."""
    return redirect(url_for('prode_bp.index'))


@main_bp.route('/logout')
@login_required
def logout():
    """
    Cierra la sesión del usuario actual.
    Si se autenticó con Microsoft Entra, también lo desloguea de Microsoft.
    """
    from flask import current_app
    from flask_login import logout_user

    proveedor = session.get('auth_provider')
    logout_user()
    session.clear()

    if proveedor == 'entra':
        tenant_id   = current_app.config.get('AZURE_TENANT_ID', '')
        post_logout = url_for('auth_bp.login', _external=True)
        entra_logout = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={post_logout}"
        )
        return redirect(entra_logout)

    return redirect(url_for('auth_bp.login'))
