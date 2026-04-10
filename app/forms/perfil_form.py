# app/forms/perfil_form.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class PerfilForm(FlaskForm):
    apellido = StringField('Apellido', validators=[DataRequired(), Length(max=50)])
    nombre   = StringField('Nombre',   validators=[DataRequired(), Length(max=50)])
    username = StringField('Usuario',  validators=[DataRequired(), Length(max=50)])
    email    = StringField('Email',    validators=[Optional(), Email(), Length(max=120)])

    password_actual = PasswordField('Contraseña actual', validators=[Optional()])
    password_nuevo  = PasswordField('Nueva contraseña',  validators=[
        Optional(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
    ])
    password_confirmar = PasswordField('Confirmar nueva contraseña', validators=[
        Optional(),
        EqualTo('password_nuevo', message='Las contraseñas no coinciden.'),
    ])

    foto = FileField('Foto de perfil', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo JPG, PNG o WEBP.'),
    ])
