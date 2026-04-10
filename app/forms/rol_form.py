# app/forms/rol_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length


class RolForm(FlaskForm):
    nombre      = StringField('Nombre',      validators=[DataRequired(), Length(max=100)])
    descripcion = TextAreaField('Descripción')
