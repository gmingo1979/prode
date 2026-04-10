# app/models/usuario.py

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import db

# Tabla de asociación usuario ↔ rol
usuario_rol = db.Table(
    'usuario_rol',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('rol_id',     db.Integer, db.ForeignKey('roles.id'),    primary_key=True),
)


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id            = db.Column(db.Integer, primary_key=True)
    apellido      = db.Column(db.String(50),  nullable=False)
    nombre        = db.Column(db.String(50),  nullable=False)
    username      = db.Column(db.String(50),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)

    # estado: Activo | Bloqueado | Retirado
    estado      = db.Column(db.String(20), default='Bloqueado', nullable=False)
    # auth_origen: Local | Google
    auth_origen = db.Column(db.String(10), default='Local',     nullable=False)
    # ID único de la cuenta Google (solo para auth_origen='Google')
    google_id   = db.Column(db.String(120), unique=True, nullable=True)

    fecha_alta = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    # URL externa de foto de perfil (ej: Google profile picture)
    foto_url   = db.Column(db.String(500), nullable=True)

    # ── Relaciones ───────────────────────────────────────────
    roles = db.relationship(
        'Rol',
        secondary='usuario_rol',
        back_populates='usuarios'
    )

    # ── Métodos de autenticación ─────────────────────────────
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def puede_ingresar(self) -> bool:
        return self.estado == 'Activo'

    # ── Propiedades calculadas ───────────────────────────────
    @property
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}"

    @property
    def profile_pic(self) -> str:
        """Ruta relativa dentro de static/. Usar avatar_url en templates."""
        import os
        ruta = f"uploads/profile_pics/user_{self.id}.jpg"
        path_fisico = os.path.join(
            os.path.dirname(__file__), '..', 'static', ruta
        )
        if os.path.exists(os.path.normpath(path_fisico)):
            return ruta
        return 'img/default.svg'

    @property
    def avatar_url(self) -> str:
        """URL completa para mostrar el avatar. Prioridad: foto local → foto_url (Google) → default."""
        import os
        from flask import url_for, current_app
        ruta = f"uploads/profile_pics/user_{self.id}.jpg"
        path_fisico = os.path.join(current_app.static_folder, ruta)
        if os.path.exists(path_fisico):
            return url_for('static', filename=ruta)
        if self.foto_url:
            return self.foto_url
        return url_for('static', filename='img/default.svg')

    def __repr__(self) -> str:
        return f"<Usuario {self.username}>"
