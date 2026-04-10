# app/models/__init__.py
# Importa todos los modelos para que Alembic los detecte al generar migraciones.

from app.models.usuario      import Usuario       # noqa: F401
from app.models.rol          import Rol           # noqa: F401
from app.models.funcion      import Funcion       # noqa: F401
from app.models.rol_funcion  import RolFuncion    # noqa: F401
from app.models.sesion_activa import SesionActiva # noqa: F401
from app.models.prode        import (             # noqa: F401
    ProdeTorneo,
    ProdeFase,
    ProdeEquipo,
    ProdePartido,
    ProdePronostico,
    ProdeInscripcion,
    ProdeConfigPuntaje,
)
