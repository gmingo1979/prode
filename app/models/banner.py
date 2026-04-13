# app/models/banner.py
#
# Banners publicitarios con rotación y conteo de clicks.
# Posiciones soportadas: header / sidebar / footer / ranking / dashboard

from datetime import datetime, timezone, date

from flask import url_for
from app.db import db

# Posiciones disponibles con guía de tamaños y formatos recomendados.
# La clave es el valor guardado en DB; el dict contiene la info de UX.
POSICION_INFO = {
    'header': {
        'label':   'Header — debajo del menú, ancho completo',
        'ejemplo': '970 × 90 px  (leaderboard estándar)',
        'ratio':   'Horizontal — proporción aprox. 10:1 a 16:3',
        'peso':    '≤ 300 KB',
        'formatos':'JPG, PNG, WebP',
    },
    'footer': {
        'label':   'Footer — sobre el pie de página',
        'ejemplo': '970 × 90 px  (leaderboard estándar)',
        'ratio':   'Horizontal — proporción aprox. 10:1 a 16:3',
        'peso':    '≤ 300 KB',
        'formatos':'JPG, PNG, WebP',
    },
    'sidebar': {
        'label':   'Sidebar — pie del panel lateral',
        'ejemplo': '300 × 250 px  (medium rectangle)',
        'ratio':   'Cuadrado o vertical — proporción aprox. 6:5 o 1:2',
        'peso':    '≤ 200 KB',
        'formatos':'JPG, PNG, WebP',
    },
    'ranking': {
        'label':   'Ranking — debajo del encabezado de la página',
        'ejemplo': '728 × 90 px  (leaderboard) o 728 × 180 px',
        'ratio':   'Horizontal — proporción aprox. 8:1 a 4:1',
        'peso':    '≤ 300 KB',
        'formatos':'JPG, PNG, WebP',
    },
    'dashboard': {
        'label':   'Dashboard — debajo de las estadísticas del torneo',
        'ejemplo': '728 × 180 px o 300 × 250 px',
        'ratio':   'Horizontal o cuadrado',
        'peso':    '≤ 300 KB',
        'formatos':'JPG, PNG, WebP, GIF animado',
    },
}

# Lista de tuplas (valor, etiqueta) para el <select> del formulario
POSICIONES = [(k, v['label']) for k, v in POSICION_INFO.items()]


class Banner(db.Model):
    __tablename__ = 'banners'

    id           = db.Column(db.Integer,      primary_key=True)
    titulo       = db.Column(db.String(120),  nullable=False)          # nombre interno
    imagen_path  = db.Column(db.String(255),  nullable=True)           # relativo a static/
    url_destino  = db.Column(db.String(500),  nullable=True)           # URL de click
    posicion     = db.Column(db.String(30),   nullable=False)
    activo       = db.Column(db.Boolean,      default=True,  nullable=False)
    fecha_desde  = db.Column(db.Date,         nullable=True)
    fecha_hasta  = db.Column(db.Date,         nullable=True)
    orden        = db.Column(db.Integer,      default=0,     nullable=False)
    clicks       = db.Column(db.Integer,      default=0,     nullable=False)
    created_at   = db.Column(db.DateTime,
                             default=lambda: datetime.now(timezone.utc))

    # ── Propiedades de conveniencia ─────────────────────────────────────────

    @property
    def imagen_src(self):
        """URL pública de la imagen para usar en <img src="">."""
        if self.imagen_path:
            return url_for('static', filename=self.imagen_path)
        return ''

    @property
    def esta_vigente(self):
        """True si el banner está activo y dentro del rango de fechas."""
        if not self.activo:
            return False
        hoy = date.today()
        if self.fecha_desde and hoy < self.fecha_desde:
            return False
        if self.fecha_hasta and hoy > self.fecha_hasta:
            return False
        return True

    @property
    def posicion_label(self):
        return dict(POSICIONES).get(self.posicion, self.posicion)

    def __repr__(self):
        return f'<Banner {self.id} [{self.posicion}] {self.titulo!r}>'
