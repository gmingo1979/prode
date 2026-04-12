# app/models/config_app.py
#
# Configuración visual de la aplicación (singleton — siempre id=1).
# Almacena los colores personalizables que sobreescriben las variables CSS.

from app.db import db


class ConfigApp(db.Model):
    __tablename__ = 'config_app'

    id = db.Column(db.Integer, primary_key=True)

    # Color principal: sidebar, botones, brand, login
    color_primary = db.Column(db.String(7), nullable=False, default='#003263')
    # Color de acento: links activos, indicadores
    color_accent  = db.Column(db.String(7), nullable=False, default='#0066cc')

    @classmethod
    def obtener(cls):
        """Devuelve la instancia única de configuración, creándola si no existe."""
        config = cls.query.get(1)
        if config is None:
            config = cls(id=1)
            db.session.add(config)
            db.session.commit()
        return config
