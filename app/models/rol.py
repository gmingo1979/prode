# app/models/rol.py
#
# Modelo de rol (grupo de permisos).
# Un usuario puede tener múltiples roles.
# Un rol puede tener múltiples funciones (permisos/ítems de menú).

from app.db import db


class Rol(db.Model):
    __tablename__ = 'roles'

    id          = db.Column(db.Integer,     primary_key=True)
    nombre      = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text,        nullable=True)

    # ── Relaciones ───────────────────────────────────────────
    usuarios = db.relationship(
        'Usuario',
        secondary='usuario_rol',
        back_populates='roles'
    )
    funciones = db.relationship(
        'Funcion',
        secondary='rol_funcion',
        back_populates='roles'
    )

    def __repr__(self) -> str:
        return f"<Rol {self.nombre}>"
