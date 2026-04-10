# app/db.py
#
# Instancia única de SQLAlchemy para toda la app.
# Se importa desde los modelos y desde __init__.py.
#
# Por qué está separado de __init__.py:
#   Evita importaciones circulares. Los modelos importan `db` desde acá,
#   y __init__.py inicializa `db` con la app usando db.init_app(flask_app).

from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

# Instancia de rate limiter — se inicializa con init_app() en create_app()
# Se importa en las rutas con: from app.db import limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[])
