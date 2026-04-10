# app/utils/menu.py
#
# Construye el menú de navegación según los roles del usuario actual.
# Devuelve un dict {categoria: [Funcion, ...]} listo para iterar en templates.

from flask_login import current_user


def obtener_menu_usuario(ubicacion: str) -> dict:
    """
    Devuelve las funciones de menú del usuario agrupadas por categoría.

    Args:
        ubicacion: 'sidebar' o 'navbar'

    Returns:
        Dict ordenado {categoria: [Funcion, ...]}
    """
    if not current_user or not current_user.is_authenticated:
        return {}

    # Deduplicar funciones por id (un usuario puede tener varios roles con la misma función)
    vistas = {}
    for rol in current_user.roles:
        for funcion in rol.funciones:
            if funcion.es_menu and funcion.ubicacion_menu == ubicacion:
                vistas[funcion.id] = funcion

    # Agrupar por categoría manteniendo orden
    resultado = {}
    for funcion in sorted(vistas.values(), key=lambda f: (f.categoria or '', f.nombre)):
        cat = funcion.categoria or 'General'
        resultado.setdefault(cat, []).append(funcion)

    return resultado
