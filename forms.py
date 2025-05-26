from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class UploadForm(FlaskForm):
    file = FileField('Archivo Excel', validators=[DataRequired()])
    submit = SubmitField('Cargar')

class VehiculoForm(FlaskForm):
    id_vehiculo = StringField('ID Vehículo', validators=[DataRequired()])
    # Agrega aquí los campos editables según las hojas de Excel
    submit = SubmitField('Guardar Cambios')
