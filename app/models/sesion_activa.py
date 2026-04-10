# app/models/sesion_activa.py
#
# Registra las sesiones activas de usuarios logueados.
# Se actualiza en cada request via before_request en __init__.py.
# Permite al Administrador ver quién está conectado y forzar cierres de sesión.

from datetime import datetime, timezone, timedelta
from app.db import db


TIMEOUT_MINUTOS = 15   # minutos sin actividad → se considera inactivo


class SesionActiva(db.Model):
    __tablename__ = 'sesiones_activas'

    id            = db.Column(db.Integer, primary_key=True)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'),
                              nullable=False)
    session_token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    ip            = db.Column(db.String(45),  nullable=True)
    user_agent    = db.Column(db.String(300), nullable=True)
    primer_acceso = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc), nullable=False)
    ultimo_visto  = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc),
                              nullable=False)
    invalidada    = db.Column(db.Boolean, default=False, nullable=False)

    usuario = db.relationship('Usuario', backref=db.backref('sesiones', lazy='dynamic',
                                                             cascade='all, delete-orphan'))

    @property
    def activa(self):
        """True si hubo actividad en los últimos TIMEOUT_MINUTOS."""
        ult = self.ultimo_visto
        if ult.tzinfo is None:
            ult = ult.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ult) < timedelta(minutes=TIMEOUT_MINUTOS)

    @property
    def minutos_desde_actividad(self):
        ult = self.ultimo_visto
        if not ult:
            return None
        if ult.tzinfo is None:
            ult = ult.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ult
        return max(int(delta.total_seconds() // 60), 0)

    @property
    def dispositivo(self):
        """Devuelve una descripción corta del dispositivo/browser."""
        ua = (self.user_agent or '').lower()
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            tipo = 'Mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            tipo = 'Tablet'
        else:
            tipo = 'Desktop'

        if 'chrome' in ua and 'edg' not in ua:
            browser = 'Chrome'
        elif 'firefox' in ua:
            browser = 'Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            browser = 'Safari'
        elif 'edg' in ua:
            browser = 'Edge'
        else:
            browser = 'Otro'

        return f'{tipo} / {browser}'

    @classmethod
    def limpiar_viejas(cls):
        """Elimina sesiones inactivas hace más de 2x el timeout (housekeeping)."""
        limite = datetime.now(timezone.utc) - timedelta(minutes=TIMEOUT_MINUTOS * 2)
        cls.query.filter(cls.ultimo_visto < limite).delete()
        db.session.commit()

    def __repr__(self):
        return f'<SesionActiva user={self.usuario_id} ip={self.ip} activa={self.activa}>'
