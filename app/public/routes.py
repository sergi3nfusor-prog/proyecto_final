from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Cliente, Producto, Categoria, Inventario, ProgramaFidelizacion, Sucursal

public_bp = Blueprint("public", __name__)


def _safe_rollback():
    try:
        db.session.rollback()
    except Exception:
        pass


@public_bp.route("/")
def index():
    stats = {
        "total_productos": 0,
        "total_clientes": 0,
        "total_marcas": 0,
        "total_sucursales": 0,
    }
    marcas = []

    try:
        stats["total_productos"] = db.session.query(func.count(Producto.IDProducto)).scalar() or 0
        stats["total_clientes"] = db.session.query(func.count(Cliente.IDCliente)).scalar() or 0
        stats["total_marcas"] = db.session.query(func.count(func.distinct(Producto.marca))).scalar() or 0
        stats["total_sucursales"] = db.session.query(func.count(Sucursal.IDSucursal)).scalar() or 0

        marcas = (
            db.session.query(Producto.marca.label("marca"), func.count(Producto.IDProducto).label("total"))
            .filter(Producto.marca.isnot(None))
            .group_by(Producto.marca)
            .order_by(func.count(Producto.IDProducto).desc())
            .limit(6)
            .all()
        )
    except SQLAlchemyError as e:
        _safe_rollback()
        current_app.logger.error(f"[DB ERROR] public.index: {e}")

    return render_template("public/index.html", stats=stats, marcas=marcas)


@public_bp.route("/productos")
def productos():
    productos = []
    categorias = []

    try:
        productos = (
            db.session.query(
                Producto.IDProducto.label("idproducto"),
                Producto.nombreProducto.label("nombreproducto"),
                Producto.marca.label("marca"),
                Producto.precio.label("precio"),
                Producto.material.label("material"),
                Producto.talla.label("talla"),
                Producto.temporada.label("temporada"),
                Producto.descripcion.label("descripcion"),
                Producto.estado.label("estado"),
                Producto.accesorios.label("accesorios"),
                Producto.fechaIngreso.label("fechaingreso"),
                Inventario.stockActual.label("stockactual"),
                Inventario.stockMaximo.label("stockmaximo"),
                Inventario.stockMinimo.label("stockminimo"),
                Categoria.nombreCategoria.label("nombrecategoria"),
            )
            .outerjoin(Inventario, Producto.IDInventario == Inventario.IDInventario)
            .outerjoin(Categoria, Categoria.IDProducto == Producto.IDProducto)
            .order_by(Producto.fechaIngreso.desc().nullslast())
            .all()
        )
        categorias = (
            db.session.query(Categoria.nombreCategoria.label("nombrecategoria"))
            .filter(Categoria.nombreCategoria.isnot(None))
            .distinct()
            .order_by(Categoria.nombreCategoria)
            .all()
        )
    except SQLAlchemyError as e:
        _safe_rollback()
        current_app.logger.error(f"[DB ERROR] public.productos: {e}")

    return render_template("public/productos.html", productos=productos, categorias=categorias)


@public_bp.route("/club")
def club():
    club_data = []
    total_miembros = 0

    try:
        club_data = (
            db.session.query(
                Cliente.nombre.label("nombre"),
                Cliente.apellidoPaterno.label("apellidopaterno"),
                Cliente.apellidoMaterno.label("apellidomaterno"),
                ProgramaFidelizacion.nivel.label("nivel"),
                ProgramaFidelizacion.puntosAcumulados.label("puntosacumulados"),
                ProgramaFidelizacion.puntosFidelizacion.label("puntosfidelizacion"),
                ProgramaFidelizacion.fechaUltimaCompra.label("fechaultimacompra"),
            )
            .join(ProgramaFidelizacion, ProgramaFidelizacion.IDCliente == Cliente.IDCliente)
            .order_by(ProgramaFidelizacion.puntosAcumulados.desc().nullslast())
            .all()
        )
        total_miembros = db.session.query(func.count(ProgramaFidelizacion.IDProgramaFidelizacion)).scalar() or 0
    except SQLAlchemyError as e:
        _safe_rollback()
        current_app.logger.error(f"[DB ERROR] public.club: {e}")

    return render_template("public/club.html", club_data=club_data, total_miembros=total_miembros)


@public_bp.route("/ofertas")
def ofertas():
    ofertas = []
    try:
        # Tabla sin modelo ORM — consulta directa intencional
        ofertas = db.session.execute(text("""
            SELECT idpromocion, tipo, valor, fechainicio, fechafin, nombrepromocion
            FROM promocion
            ORDER BY fechainicio DESC
        """)).fetchall()
    except SQLAlchemyError as e:
        _safe_rollback()
        current_app.logger.error(f"[DB ERROR] public.ofertas: {e}")

    return render_template("public/ofertas.html", ofertas=ofertas)


@public_bp.route("/sedes")
def sedes():
    sedes = []
    try:
        sedes = (
            db.session.query(
                Sucursal.IDSucursal.label("idsucursal"),
                Sucursal.nombreSucursal.label("nombresucursal"),
                Sucursal.pais.label("pais"),
                Sucursal.ciudad.label("ciudad"),
                Sucursal.calle.label("calle"),
                Sucursal.numeroProvincia.label("numeroprovincia"),
                Sucursal.horarioAtencion.label("horarioatencion"),
                Sucursal.telefono.label("telefono"),
                Sucursal.correo.label("correo"),
            )
            .order_by(Sucursal.nombreSucursal)
            .all()
        )
    except SQLAlchemyError as e:
        _safe_rollback()
        current_app.logger.error(f"[DB ERROR] public.sedes: {e}")

    return render_template("public/sedes.html", sedes=sedes)


@public_bp.route("/mensajes", methods=["GET", "POST"])
def mensajes():
    if request.method == "POST":
        from app.forms import MensajeForm
        form = MensajeForm()
        if form.validate_on_submit():
            nombre = form.nombre.data[:100]
            email = form.email.data[:100]
            asunto = (form.asunto.data or "")[:100]
            mensaje = form.mensaje.data[:2000]
    
            try:
                db.session.execute(text("""
                    INSERT INTO mensaje_contacto (nombre, email, asunto, mensaje)
                    VALUES (:nombre, :email, :asunto, :mensaje)
                """), {
                    "nombre": nombre,
                    "email": email,
                    "asunto": asunto,
                    "mensaje": mensaje,
                })
                db.session.commit()
                flash("Mensaje enviado exitosamente. Nos pondremos en contacto contigo pronto.", "success")
            except SQLAlchemyError as e:
                _safe_rollback()
                current_app.logger.error(f"[DB ERROR] public.mensajes: {e}")
                flash("Error al enviar el mensaje. Intenta nuevamente.", "error")
    
            return redirect(url_for("public.mensajes"))
        else:
            if form.errors:
                 flash("Por favor completa todos los campos obligatorios correctamente.", "error")

    from app.forms import MensajeForm
    return render_template("public/mensajes.html", form=MensajeForm())
