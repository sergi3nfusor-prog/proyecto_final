from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import UsuarioEmpleado, BitacoraAcceso
from app.forms import LoginForm, RegistroForm


auth_bp = Blueprint("auth", __name__)


ROLES_VALIDOS = {"usuario", "empleado", "gerente", "admin"}


def normalizar_rol(rol):
    """Compatibilidad con roles anteriores del proyecto analítico."""
    mapa = {
        "vendedor": "empleado",
        "almacen": "empleado",
    }
    return mapa.get(rol, rol)


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
    """Permite acceso solo a roles indicados. Admin siempre tiene acceso total."""
    roles = set(roles)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.full_path))

            rol_actual = normalizar_rol(current_user.rol)
            if rol_actual == "admin" or rol_actual in roles:
                return f(*args, **kwargs)

            abort(403)
        return decorated_function
    return decorator


def _home_for_role(rol):
    rol = normalizar_rol(rol)
    if rol == "admin":
        return url_for("dashboard.ejecutivo")
    if rol == "gerente":
        return url_for("dashboard.ejecutivo")
    if rol == "empleado":
        return url_for("ventas.registrar")
    return url_for("public.index")


def _codigo_valido(rol, codigo):
    if rol == "usuario":
        return True

    codigos = {
        "empleado": current_app.config.get("ACCESS_CODE_EMPLEADO"),
        "gerente": current_app.config.get("ACCESS_CODE_GERENTE"),
        "admin": current_app.config.get("ACCESS_CODE_ADMIN"),
    }
    esperado = codigos.get(rol)
    return bool(esperado) and codigo.strip() == esperado


# ─────────────────────────────────────────────────────────────────────────────
# RUTA: Login
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home_for_role(current_user.rol))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = UsuarioEmpleado.query.filter_by(
            nombreUsuario=form.username.data.strip()
        ).first()

        if usuario and check_password_hash(usuario.contraseniaUsuario, form.password.data):
            # Normaliza roles antiguos si existen en la BD.
            rol_normalizado = normalizar_rol(usuario.rol)
            if usuario.rol != rol_normalizado:
                usuario.rol = rol_normalizado
                db.session.add(usuario)

            login_user(usuario, remember=form.remember.data)
            log_access("login", f"Acceso exitoso — rol: {usuario.rol}", user=usuario)
            db.session.commit()
            flash(f"Bienvenido, {usuario.nombreUsuario}.", "success")

            next_page = request.args.get("next")
            if next_page:
                p = urlparse(next_page)
                if p.netloc != "" or p.scheme != "" or not next_page.startswith("/"):
                    next_page = None
            return redirect(next_page or _home_for_role(usuario.rol))

        log_access(
            "login_failed",
            f"Intento fallido — usuario: {form.username.data.strip()}"
        )
        db.session.commit()
        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html", form=form)


# ─────────────────────────────────────────────────────────────────────────────
# RUTA: Registro
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(_home_for_role(current_user.rol))

    form = RegistroForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        rol = form.rol.data
        codigo = form.codigo_acceso.data or ""

        if rol not in ROLES_VALIDOS:
            flash("Rol no válido.", "danger")
            return render_template("registro.html", form=form)

        if not _codigo_valido(rol, codigo):
            flash("Código de acceso incorrecto para el rol seleccionado.", "danger")
            return render_template("registro.html", form=form)

        existente = UsuarioEmpleado.query.filter_by(nombreUsuario=username).first()
        if existente:
            flash("El nombre de usuario ya existe. Use otro usuario.", "warning")
            return render_template("registro.html", form=form)

        try:
            usuario = UsuarioEmpleado(
                nombreUsuario=username,
                contraseniaUsuario=generate_password_hash(form.password.data),
                rol=rol
            )
            db.session.add(usuario)
            db.session.flush()
            log_access("registro", f"Cuenta creada — rol: {rol}", user=usuario)
            db.session.commit()
            flash("Cuenta creada correctamente. Ahora puede iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
        except SQLAlchemyError as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            current_app.logger.error(f"[DB ERROR] registro: {e}")
            flash("No se pudo crear la cuenta. Revise la base de datos.", "danger")

    return render_template("registro.html", form=form)


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
    return redirect(url_for("public.index"))
