# app/models/prode.py
#
# Modelos del módulo Prode.
#
# Jerarquía:
#   ProdeTorneo
#     └── ProdeFase          (Grupos, Octavos, Cuartos, Semi, Final, etc.)
#           └── ProdePartido
#                 └── ProdePronostico  (1 por usuario por partido)
#     └── ProdeEquipo        (equipos/selecciones del torneo)
#     └── ProdeInscripcion   (usuario inscripto + estado de aprobación)
#   ProdeConfigPuntaje       (puntos por resultado exacto / parcial / error)

from datetime import datetime, timezone, timedelta
from app.db import db


class ProdeTorneo(db.Model):
    __tablename__ = 'prode_torneos'

    id           = db.Column(db.Integer,     primary_key=True)
    nombre       = db.Column(db.String(100), nullable=False)
    descripcion  = db.Column(db.Text,        nullable=True)
    fecha_inicio = db.Column(db.Date,        nullable=False)
    fecha_fin    = db.Column(db.Date,        nullable=False)
    activo       = db.Column(db.Boolean,     default=True)
    inscripcion_abierta = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))

    fases         = db.relationship('ProdeFase',        backref='torneo', lazy=True,
                                    order_by='ProdeFase.orden',
                                    cascade='all, delete-orphan')
    equipos       = db.relationship('ProdeEquipo',      backref='torneo', lazy=True,
                                    order_by='ProdeEquipo.grupo, ProdeEquipo.nombre',
                                    cascade='all, delete-orphan')
    inscripciones = db.relationship('ProdeInscripcion', backref='torneo', lazy=True,
                                    cascade='all, delete-orphan')
    config        = db.relationship('ProdeConfigPuntaje', backref='torneo',
                                    uselist=False, cascade='all, delete-orphan')

    @property
    def partidos(self):
        """Todos los partidos del torneo a través de las fases."""
        result = []
        for fase in self.fases:
            result.extend(fase.partidos)
        return result

    def __repr__(self):
        return f'<ProdeTorneo {self.nombre}>'


class ProdeFase(db.Model):
    """
    Representa una fase del torneo: Fase de Grupos, Octavos, Cuartos,
    Semifinales, Final, etc.
    """
    __tablename__ = 'prode_fases'

    id         = db.Column(db.Integer,    primary_key=True)
    torneo_id  = db.Column(db.Integer,    db.ForeignKey('prode_torneos.id'), nullable=False)
    nombre     = db.Column(db.String(60), nullable=False)
    orden      = db.Column(db.Integer,    default=0)
    created_at = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))

    partidos = db.relationship('ProdePartido', backref='fase', lazy=True,
                               order_by='ProdePartido.fecha_hora',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ProdeFase {self.nombre}>'


class ProdeEquipo(db.Model):
    __tablename__ = 'prode_equipos'

    id         = db.Column(db.Integer,     primary_key=True)
    torneo_id  = db.Column(db.Integer,     db.ForeignKey('prode_torneos.id'), nullable=False)
    nombre     = db.Column(db.String(100), nullable=False)
    grupo      = db.Column(db.String(10),  nullable=True)
    escudo_url = db.Column(db.String(255), nullable=True)
    codigo_iso = db.Column(db.String(10),  nullable=True)
    created_at = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ProdeEquipo {self.nombre}>'


class ProdePartido(db.Model):
    __tablename__ = 'prode_partidos'

    id                  = db.Column(db.Integer,  primary_key=True)
    fase_id             = db.Column(db.Integer,  db.ForeignKey('prode_fases.id'),   nullable=False)
    equipo_local_id     = db.Column(db.Integer,  db.ForeignKey('prode_equipos.id'), nullable=False)
    equipo_visitante_id = db.Column(db.Integer,  db.ForeignKey('prode_equipos.id'), nullable=False)
    fecha_hora          = db.Column(db.DateTime, nullable=False)
    goles_local         = db.Column(db.Integer,  nullable=True)
    goles_visitante     = db.Column(db.Integer,  nullable=True)
    estado              = db.Column(db.String(20), default='pendiente')
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    equipo_local     = db.relationship('ProdeEquipo', foreign_keys=[equipo_local_id])
    equipo_visitante = db.relationship('ProdeEquipo', foreign_keys=[equipo_visitante_id])
    pronosticos      = db.relationship('ProdePronostico', backref='partido', lazy=True,
                                       cascade='all, delete-orphan')

    @property
    def torneo(self):
        return self.fase.torneo

    @property
    def pronosticos_bloqueados(self):
        """True si ya no se puede pronosticar (menos de 2h para el inicio o cerrado)."""
        if self.estado == 'cerrado':
            return True
        ahora = datetime.now(timezone.utc)
        fh = self.fecha_hora
        if fh.tzinfo is None:
            fh = fh.replace(tzinfo=timezone.utc)
        return ahora >= fh - timedelta(hours=2)

    @property
    def resultado_str(self):
        if self.goles_local is None or self.goles_visitante is None:
            return '— : —'
        return f'{self.goles_local} : {self.goles_visitante}'

    def __repr__(self):
        return f'<ProdePartido {self.equipo_local.nombre} vs {self.equipo_visitante.nombre}>'


class ProdePronostico(db.Model):
    __tablename__ = 'prode_pronosticos'
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'partido_id', name='uq_prode_usuario_partido'),
    )

    id               = db.Column(db.Integer, primary_key=True)
    usuario_id       = db.Column(db.Integer, db.ForeignKey('usuarios.id'),       nullable=False)
    partido_id       = db.Column(db.Integer, db.ForeignKey('prode_partidos.id'), nullable=False)
    goles_local      = db.Column(db.Integer, nullable=False)
    goles_visitante  = db.Column(db.Integer, nullable=False)
    puntos           = db.Column(db.Integer, default=0)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc))

    usuario = db.relationship('Usuario', backref=db.backref('pronosticos_prode', lazy=True))

    def __repr__(self):
        return f'<ProdePronostico U:{self.usuario_id} P:{self.partido_id} {self.goles_local}-{self.goles_visitante}>'


class ProdeInscripcion(db.Model):
    """
    Un usuario se inscribe a un torneo. El admin aprueba o rechaza.
    Estados: pendiente | aprobado | rechazado
    """
    __tablename__ = 'prode_inscripciones'
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'torneo_id', name='uq_prode_inscripcion'),
    )

    id         = db.Column(db.Integer,    primary_key=True)
    usuario_id = db.Column(db.Integer,    db.ForeignKey('usuarios.id'),      nullable=False)
    torneo_id  = db.Column(db.Integer,    db.ForeignKey('prode_torneos.id'), nullable=False)
    estado     = db.Column(db.String(20), default='pendiente')
    created_at = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship('Usuario', backref=db.backref('inscripciones_prode', lazy=True))

    def __repr__(self):
        return f'<ProdeInscripcion U:{self.usuario_id} T:{self.torneo_id} {self.estado}>'


class ProdeConfigPuntaje(db.Model):
    """
    Configuración de puntos por torneo.
    resultado_exacto  : marcador exacto (ej: 3 pts)
    resultado_parcial : ganador correcto pero marcador errado (ej: 1 pt)
    resultado_errado  : resultado completamente errado (ej: 0 pts)
    """
    __tablename__ = 'prode_config_puntaje'

    id                = db.Column(db.Integer, primary_key=True)
    torneo_id         = db.Column(db.Integer, db.ForeignKey('prode_torneos.id'),
                                  nullable=False, unique=True)
    resultado_exacto  = db.Column(db.Integer, default=3)
    resultado_parcial = db.Column(db.Integer, default=1)
    resultado_errado  = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<ProdeConfigPuntaje T:{self.torneo_id} {self.resultado_exacto}/{self.resultado_parcial}/{self.resultado_errado}>'
