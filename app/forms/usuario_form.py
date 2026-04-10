# app/forms/usuario_form.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, SelectField, SelectMultipleField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class UsuarioForm(FlaskForm):
    apellido    = StringField('Apellido', validators=[DataRequired(), Length(max=50)])
    nombre      = StringField('Nombre',   validators=[DataRequired(), Length(max=50)])
    username    = StringField('Usuario',  validators=[DataRequired(), Length(max=50)])
    email       = StringField('Email',    validators=[Optional(), Email(), Length(max=120)])

    password = PasswordField('Contraseña', validators=[Optional(), Length(min=8,
                             message='La contraseña debe tener al menos 8 caracteres.')])
    password_confirmar = PasswordField('Confirmar contraseña', validators=[
        Optional(),
        EqualTo('password', message='Las contraseñas no coinciden.'),
    ])

    estado = SelectField('Estado', choices=[
        ('Activo',    'Activo'),
        ('Bloqueado', 'Bloqueado'),
        ('Retirado',  'Retirado'),
    ])
    auth_origen = SelectField('Origen de autenticación', choices=[
        ('Local',  'Local (usuario y contraseña)'),
        ('Google', 'Google'),
    ])

    roles = SelectMultipleField('Roles', coerce=int)
    foto  = FileField('Foto de perfil', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo JPG, PNG o WEBP.'),
    ])
