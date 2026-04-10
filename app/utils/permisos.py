# app/utils/permisos.py
#
# Decorador de control de acceso basado en roles (RBAC).
# Verifica que el usuario tenga una Funcion cuyo endpoint coincida
# con el endpoint actual del request.

from functools import wraps

from flask import abort, request
from flask_login import current_user


def requiere_funcion():
    """
    Decorador que restringe el acceso a usuarios con una Funcion
    que tenga el mismo endpoint que la vista decorada.

    Uso:
        @roles_bp.route('/roles/')
        @login_required
        @requiere_funcion()
        def listado():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            endpoint = request.endpoint
            for rol in current_user.roles:
                for funcion in rol.funciones:
                    if funcion.endpoint == endpoint:
                        return f(*args, **kwargs)

            abort(403)

        return decorated
    return decorator
