from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    IntegerField, DecimalField, SelectField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, EqualTo


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


class RegistroForm(FlaskForm):
    """Registro único para usuario público y personal interno."""
    username = StringField(
        "Usuario",
        validators=[DataRequired(message="El usuario es requerido."),
                    Length(min=3, max=80, message="Debe tener entre 3 y 80 caracteres.")]
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="La contraseña es requerida."),
                    Length(min=6, max=128, message="Debe tener al menos 6 caracteres.")]
    )
    confirm_password = PasswordField(
        "Confirmar contraseña",
        validators=[DataRequired(message="Confirme la contraseña."),
                    EqualTo("password", message="Las contraseñas no coinciden.")]
    )
    rol = SelectField(
        "Tipo de cuenta",
        choices=[
            ("usuario", "Usuario / Cliente"),
            ("empleado", "Empleado"),
            ("gerente", "Gerente"),
            ("admin", "Administrador"),
        ],
        validators=[DataRequired(message="Seleccione un tipo de cuenta.")]
    )
    codigo_acceso = StringField(
        "Código de acceso",
        validators=[Optional(), Length(max=100)]
    )
    submit = SubmitField("Crear cuenta")


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


class MensajeForm(FlaskForm):
    """Formulario de contacto público."""
    nombre = StringField(
        "Nombre Completo",
        validators=[DataRequired(message="El nombre es requerido."),
                    Length(max=100, message="Máximo 100 caracteres.")]
    )
    email = StringField(
        "Correo Electrónico",
        validators=[DataRequired(message="El correo es requerido."),
                    Length(max=100, message="Máximo 100 caracteres.")]
    )
    asunto = StringField(
        "Asunto",
        validators=[Optional(), Length(max=100)]
    )
    mensaje = StringField(
        "Mensaje",
        validators=[DataRequired(message="El mensaje es requerido."),
                    Length(max=2000, message="Máximo 2000 caracteres.")]
    )
    submit = SubmitField("Enviar Mensaje")
