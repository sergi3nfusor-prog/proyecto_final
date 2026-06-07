from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    IntegerField, DecimalField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class LoginForm(FlaskForm):
    """Formulario de inicio de sesión."""
    username = StringField(
        "Usuario",
        validators=[DataRequired(message="El usuario es requerido."),
                    Length(max=80, message="Máximo 80 caracteres.")]
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="La contraseña es requerida."),
                    Length(max=128, message="Máximo 128 caracteres.")]
    )
    remember = BooleanField("Recordarme")
    submit   = SubmitField("Ingresar")


class VentaForm(FlaskForm):
    """Formulario de registro de venta en caja."""
    id_cliente   = IntegerField(
        "ID del Cliente",
        validators=[DataRequired(message="Ingrese el ID del cliente."),
                    NumberRange(min=1, message="ID debe ser mayor a 0.")]
    )
    id_producto  = IntegerField(
        "ID del Producto",
        validators=[DataRequired(message="Ingrese el ID del producto."),
                    NumberRange(min=1, message="ID debe ser mayor a 0.")]
    )
    cantidad     = IntegerField(
        "Cantidad",
        validators=[DataRequired(message="Ingrese la cantidad."),
                    NumberRange(min=1, message="La cantidad debe ser al menos 1.")]
    )
    descuento    = DecimalField(
        "Descuento (Bs)",
        places=2,
        validators=[Optional()],
        default=0.00
    )
    razon_social = StringField(
        "Razón Social",
        validators=[Optional(), Length(max=45)]
    )
    nit          = StringField(
        "NIT",
        validators=[Optional(), Length(max=45)]
    )
    submit       = SubmitField("Registrar Venta")
