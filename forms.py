from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, NumberRange, ValidationError
from models import Categoria, Cliente, Producto

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Ingresar')

class RegistroForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    rol = SelectField('Rol', choices=[('admin', 'Administrador'), ('trabajador', 'Trabajador')])
    submit = SubmitField('Registrar Usuario')

class CategoriaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    submit = SubmitField('Guardar')

class ProveedorForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    telefono = StringField('Teléfono')
    submit = SubmitField('Guardar')

class ProductoForm(FlaskForm):
    codigo = StringField('Código Único', validators=[DataRequired()])
    nombre = StringField('Nombre Producto', validators=[DataRequired()])
    precio = DecimalField('Precio', validators=[DataRequired(), NumberRange(min=0.01)])
    stock = IntegerField('Stock Inicial', validators=[DataRequired(), NumberRange(min=0)])
    stock_minimo = IntegerField('Stock Mínimo', validators=[DataRequired()])
    categoria_id = SelectField('Categoría', coerce=int)
    proveedor_id = SelectField('Proveedor', coerce=int)
    submit = SubmitField('Guardar')

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono')
    submit = SubmitField('Guardar')