# app/models/rol_funcion.py
#
# Tabla de asociación entre Rol y Funcion (many-to-many).

from app.db import db

RolFuncion = db.Table(
    'rol_funcion',
    db.Column('rol_id',     db.Integer, db.ForeignKey('roles.id'),     primary_key=True),
    db.Column('funcion_id', db.Integer, db.ForeignKey('funciones.id'), primary_key=True),
)
