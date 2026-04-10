# run.py
#
# Punto de entrada de la aplicación.
# Ejecutar con:   python run.py
# O con Flask:    flask --app run run --debug
#
# En producción usar Gunicorn:
#   gunicorn "run:flask_app" --bind 0.0.0.0:8000 --workers 4

from app import create_app

# ── App ───────────────────────────────────────────────────────
flask_app = create_app()

if __name__ == '__main__':
    flask_app.run(host="0.0.0.0", debug=True)