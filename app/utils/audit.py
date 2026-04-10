# app/utils/audit.py
#
# Registro de auditoría de acciones del sistema.
# Las acciones se escriben en el log de la aplicación (nivel INFO).
# En producción podés redirigir este logger a un archivo separado.

import logging

logger = logging.getLogger('audit')


def registrar_accion(accion: str, entidad: str, entidad_id: int, detalle: str = '') -> None:
    """
    Registra una acción del usuario actual sobre una entidad.

    Args:
        accion:     Tipo de acción ('crear', 'editar', 'eliminar', etc.)
        entidad:    Nombre de la entidad afectada ('usuario', 'rol', etc.)
        entidad_id: ID del registro afectado
        detalle:    Información adicional (campos modificados, etc.)
    """
    from flask_login import current_user

    usuario = (
        current_user.username
        if current_user and current_user.is_authenticated
        else 'sistema'
    )

    logger.info(
        '[%s] %s#%s por %s — %s',
        accion.upper(), entidad, entidad_id, usuario, detalle
    )
