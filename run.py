# run.py
#
# Punto de entrada de la aplicación.
# Ejecutar con:   python run.py
# O con Flask:    flask --app run run --debug
#
# En producción usar Gunicorn:
#   buildCommand: pip install --prefer-binary -r requirements.txt && mkdir -p /opt/render/project/data && python -m flask db upgrade
#   startCommand: gunicorn "run:flask_app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120

from app import create_app

# ── App ───────────────────────────────────────────────────────
flask_app = create_app()

if __name__ == '__main__':
    flask_app.run(host="0.0.0.0", port=5022, debug=True)