from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app import db
from app.models import UsuarioEmpleado, BitacoraAcceso
from app.forms import LoginForm

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Registrar en bitácora de acceso
# ─────────────────────────────────────────────────────────────────────────────

def log_access(action: str, detail: str = "", user=None):
    """
    Inserta una fila en bitacora_acceso.
    NO hace commit; la ruta llamadora es responsable del commit.
    """
    ip = (
        request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        or request.remote_addr
    )
    uid = None
    if user is not None:
        uid = user.IDUsuarioEmpleado
    elif current_user.is_authenticated:
        uid = current_user.IDUsuarioEmpleado

    entrada = BitacoraAcceso(
        usuario_id=uid,
        ip=ip,
        accion=action,
        detalle=detail[:255] if detail else ""
    )
    db.session.add(entrada)


# ─────────────────────────────────────────────────────────────────────────────
# DECORADOR: control de roles
# ─────────────────────────────────────────────────────────────────────────────

def role_required(*roles):
    """
    Decorador que verifica que el usuario autenticado tenga uno de los roles
    indicados. Si no está autenticado → login. Si no tiene el rol → 403.
    Uso: @role_required("admin", "vendedor")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# RUTA: Login
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.ejecutivo"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = UsuarioEmpleado.query.filter_by(
            nombreUsuario=form.username.data.strip()
        ).first()

        if usuario and check_password_hash(usuario.contraseniaUsuario, form.password.data):
            login_user(usuario, remember=form.remember.data)
            log_access("login", f"Acceso exitoso — rol: {usuario.rol}", user=usuario)
            db.session.commit()
            flash(f"¡Bienvenido, {usuario.nombreUsuario}! 👋", "success")

            # Redirigir al next solo si el usuario tiene permiso según su rol
            next_page = request.args.get("next")

            # Determinar página de inicio según rol
            if usuario.rol == "admin":
                default_page = url_for("dashboard.ejecutivo")
            elif usuario.rol == "vendedor":
                default_page = url_for("ventas.registrar")
            elif usuario.rol == "almacen":
                default_page = url_for("inventario.productos")
            else:
                default_page = url_for("ventas.historial")

            return redirect(next_page or default_page)
        else:
            log_access(
                "login_failed",
                f"Intento fallido — usuario: {form.username.data.strip()}"
            )
            db.session.commit()
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html", form=form)


# ─────────────────────────────────────────────────────────────────────────────
# RUTA: Logout
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    log_access("logout", f"Sesión cerrada — usuario: {current_user.nombreUsuario}")
    db.session.commit()
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
