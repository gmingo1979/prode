# app/models/grupo.py
#
# Grupos privados entre usuarios del Prode.
#
# ProdeGrupo          → grupo creado por un usuario
# ProdeGrupoMiembro   → asociación usuario ↔ grupo
# ProdeGrupoInvitacion → invitación por email (con token único)

import secrets
import string
from datetime import datetime, timezone

from app.db import db

_CODIGO_CHARS = string.ascii_uppercase + string.digits


def _generar_codigo():
    return ''.join(secrets.choice(_CODIGO_CHARS) for _ in range(8))


class ProdeGrupo(db.Model):
    __tablename__ = 'prode_grupos'

    id          = db.Column(db.Integer,     primary_key=True)
    nombre      = db.Column(db.String(80),  nullable=False)
    descripcion = db.Column(db.String(200), nullable=True)
    codigo      = db.Column(db.String(8),   nullable=False, unique=True,
                            default=_generar_codigo)
    creador_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creador     = db.relationship('Usuario', foreign_keys=[creador_id],
                                  backref=db.backref('grupos_creados', lazy=True))
    miembros    = db.relationship('ProdeGrupoMiembro', backref='grupo',
                                  lazy=True, cascade='all, delete-orphan')
    invitaciones = db.relationship('ProdeGrupoInvitacion', backref='grupo',
                                   lazy=True, cascade='all, delete-orphan')

    def es_miembro(self, usuario_id):
        return any(m.usuario_id == usuario_id for m in self.miembros)

    def cantidad_miembros(self):
        return len(self.miembros)

    def __repr__(self):
        return f'<ProdeGrupo {self.nombre} [{self.codigo}]>'


class ProdeGrupoMiembro(db.Model):
    __tablename__ = 'prode_grupo_miembros'
    __table_args__ = (
        db.UniqueConstraint('grupo_id', 'usuario_id', name='uq_grupo_miembro'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    grupo_id   = db.Column(db.Integer, db.ForeignKey('prode_grupos.id'),  nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'),      nullable=False)
    rol        = db.Column(db.String(20), default='miembro')  # 'creador' | 'miembro'
    joined_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship('Usuario',
                              backref=db.backref('membresias_grupo', lazy=True))

    def __repr__(self):
        return f'<ProdeGrupoMiembro G:{self.grupo_id} U:{self.usuario_id}>'


class ProdeGrupoInvitacion(db.Model):
    __tablename__ = 'prode_grupo_invitaciones'

    id             = db.Column(db.Integer,    primary_key=True)
    grupo_id       = db.Column(db.Integer,    db.ForeignKey('prode_grupos.id'), nullable=False)
    email          = db.Column(db.String(120), nullable=False)
    token          = db.Column(db.String(64), nullable=False, unique=True,
                               default=lambda: secrets.token_urlsafe(32))
    estado         = db.Column(db.String(20), default='pendiente')  # 'pendiente' | 'aceptada'
    invitado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    invitado_por = db.relationship('Usuario', foreign_keys=[invitado_por_id])

    def __repr__(self):
        return f'<ProdeGrupoInvitacion G:{self.grupo_id} {self.email} {self.estado}>'
