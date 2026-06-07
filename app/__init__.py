import os
import click
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

from .config import Config

# ── Extensiones globales ──────────────────────────────────────────────────────
db           = SQLAlchemy()
migrate      = Migrate()
login_manager = LoginManager()
csrf         = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Inicializar extensiones ───────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Flask-Login config ────────────────────────────────────────────────────
    login_manager.login_view     = "auth.login"
    login_manager.login_message  = "Por favor inicia sesión para continuar."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from .models import UsuarioEmpleado
        return db.session.get(UsuarioEmpleado, int(user_id))

    # ── Registrar Blueprints ──────────────────────────────────────────────────
    from .auth.routes      import auth_bp
    from .ventas.routes    import ventas_bp
    from .inventario.routes import inventario_bp
    from .dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ventas_bp,    url_prefix="/ventas")
    app.register_blueprint(inventario_bp, url_prefix="/inventario")
    app.register_blueprint(dashboard_bp,  url_prefix="/dashboard")

    # ── Ruta raíz ────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return redirect(url_for("dashboard.ejecutivo"))

    # ── CLI: flask create-admin ───────────────────────────────────────────────
    @app.cli.command("create-admin")
    def create_admin():
        """Crea o actualiza el usuario administrador desde .env."""
        from .models import UsuarioEmpleado

        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "AdminSeguro123")

        usuario = UsuarioEmpleado.query.filter_by(nombreUsuario=username).first()
        if usuario:
            usuario.contraseniaUsuario = generate_password_hash(password)
            usuario.rol = "admin"
            click.echo(f"[✓] Usuario '{username}' actualizado como admin.")
        else:
            usuario = UsuarioEmpleado(
                nombreUsuario      = username,
                contraseniaUsuario = generate_password_hash(password),
                rol                = "admin"
            )
            db.session.add(usuario)
            click.echo(f"[✓] Admin '{username}' creado exitosamente.")

        db.session.commit()

    # ── CLI: flask fix-users ──────────────────────────────────────────────────
    @app.cli.command("fix-users")
    def fix_users():
        """Hashea contraseñas planas de usuarios existentes y les asigna el rol vendedor."""
        from .models import UsuarioEmpleado
        
        usuarios = UsuarioEmpleado.query.all()
        actualizados = 0
        
        for u in usuarios:
            # Los hashes de werkzeug empiezan con pbkdf2: o scrypt:
            if not u.contraseniaUsuario.startswith("pbkdf2:") and not u.contraseniaUsuario.startswith("scrypt:"):
                # Capturamos la contraseña actual, que está en texto plano, y la encriptamos
                u.contraseniaUsuario = generate_password_hash(u.contraseniaUsuario)
                if not u.rol or u.rol not in ["admin", "vendedor", "almacen"]:
                    u.rol = "vendedor"  # Rol por defecto para que puedan acceder a la caja
                actualizados += 1
                
        db.session.commit()
        click.echo(f"[✓] Éxito: {actualizados} usuarios existentes han sido encriptados y asignados como vendedores.")

    return app
