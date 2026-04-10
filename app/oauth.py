# app/oauth.py
#
# Instancia de OAuth (authlib) compartida.
# Se inicializa con init_app() en create_app().

from authlib.integrations.flask_client import OAuth

oauth = OAuth()
