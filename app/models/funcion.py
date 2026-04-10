# app/models/funcion.py
#
# Modelo de función (permiso/ítem de menú).
# Representa tanto un permiso de acceso como un ítem navegable del sistema.
#
# Campos clave:
#   endpoint        → nombre del endpoint Flask (ej: 'prode_bp.index')
#   es_menu         → si True, aparece en el menú de navegación
#   ubicacion_menu  → 'sidebar' o 'navbar'
#   categoria       → agrupa ítems en el sidebar (ej: 'Prode')
#   icono           → clase Bootstrap Icons (ej: 'bi bi-trophy')

from app.db import db


class Funcion(db.Model):
    __tablename__ = 'funciones'

    id             = db.Column(db.Integer,     primary_key=True)
    nombre         = db.Column(db.String(100), unique=True, nullable=False)
    endpoint       = db.Column(db.String(100), unique=True, nullable=False)
    descripcion    = db.Column(db.Text,        nullable=True)
    icono          = db.Column(db.String(100), nullable=True)
    categoria      = db.Column(db.String(100), nullable=True)
    es_menu        = db.Column(db.Boolean,     default=False)
    ubicacion_menu = db.Column(db.String(20),  default='sidebar')

    # ── Relaciones ───────────────────────────────────────────
    roles = db.relationship(
        'Rol',
        secondary='rol_funcion',
        back_populates='funciones'
    )

    def __repr__(self) -> str:
        return f"<Funcion {self.nombre}>"
