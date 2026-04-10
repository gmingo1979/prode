# app/forms/funcion_form.py

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class FuncionForm(FlaskForm):
    nombre         = StringField('Nombre',    validators=[DataRequired(), Length(max=100)])
    endpoint       = StringField('Endpoint',  validators=[DataRequired(), Length(max=100)])
    descripcion    = TextAreaField('Descripción')
    icono          = StringField('Ícono',     validators=[Optional(), Length(max=100)])
    categoria      = StringField('Categoría', validators=[Optional(), Length(max=100)])
    es_menu        = BooleanField('Mostrar en menú')
    ubicacion_menu = SelectField(
        'Ubicación en menú',
        choices=[('sidebar', 'Sidebar'), ('navbar', 'Navbar')],
        default='sidebar',
    )
