# app/utils/imagen_utils.py
#
# Procesamiento de imágenes para fotos de perfil de usuarios.

import os

from flask import current_app
from PIL import Image

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_SIZE = (400, 400)


def _foto_path(usuario_id: int) -> str:
    return os.path.join(
        current_app.config['UPLOAD_PROFILE_PICS_FOLDER'],
        f'user_{usuario_id}.jpg'
    )


def procesar_y_guardar_foto(file_storage, usuario_id: int) -> None:
    """
    Redimensiona y guarda la foto de perfil como JPEG 400×400 máx.

    Raises:
        ValueError: si el formato no está permitido.
    """
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Formato no permitido. Usá JPG, PNG o WEBP.')

    img = Image.open(file_storage)
    img.thumbnail(MAX_SIZE, Image.LANCZOS)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    img.save(_foto_path(usuario_id), 'JPEG', quality=85)


def eliminar_foto(usuario_id: int) -> None:
    """Elimina la foto de perfil del usuario si existe."""
    path = _foto_path(usuario_id)
    if os.path.exists(path):
        os.remove(path)
