from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text

from app import db
from app.models import Venta, Cliente, Producto
from app.forms import VentaForm
from app.auth.routes import log_access, role_required

ventas_bp = Blueprint("ventas", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: Registrar venta
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/registrar", methods=["GET", "POST"])
@login_required
@role_required("vendedor", "admin")
def registrar():
    form = VentaForm()

    if form.validate_on_submit():
        try:
            p_descuento = float(form.descuento.data or 0)
            db.session.execute(
                text("""
                    CALL sp_registrar_venta_integral(
                        :id_cliente, :id_empleado, :id_producto,
                        :cantidad, :precio_unitario, :descuento_venta,
                        :razon_social, :nit
                    )
                """),
                {
                    "id_cliente":      form.id_cliente.data,
                    "id_empleado":     _get_empleado_id(),
                    "id_producto":     form.id_producto.data,
                    "cantidad":        form.cantidad.data,
                    "precio_unitario": float(
                        db.session.execute(
                            text("SELECT fn_precio_producto(:id)"),
                            {"id": form.id_producto.data}
                        ).scalar()
                    ),
                    "descuento_venta": p_descuento,
                    "razon_social":    form.razon_social.data or "S/N",
                    "nit":             form.nit.data or "0",
                }
            )
            db.session.commit()
            log_access(
                "venta_registrada",
                f"Cliente={form.id_cliente.data} Producto={form.id_producto.data} "
                f"Cantidad={form.cantidad.data}"
            )
            db.session.commit()
            flash("✅ Venta registrada exitosamente.", "success")
            return redirect(url_for("ventas.registrar"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al registrar la venta: {str(e)}", "danger")

    return render_template("ventas/registrar_venta.html", form=form)


def _get_empleado_id():
    """Obtiene el IDEmpleado del usuario actual (si tiene empleado asociado)."""
    if current_user.empleado:
        return current_user.empleado.IDEmpleado
    # Fallback: buscar el primer empleado ligado al usuario
    from app.models import Empleado
    emp = Empleado.query.filter_by(IDUsuarioEmpleado=current_user.IDUsuarioEmpleado).first()
    return emp.IDEmpleado if emp else 1


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: Historial de ventas
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/historial")
@login_required
@role_required("vendedor", "admin")
def historial():
    return render_template("ventas/historial_ventas.html")


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Historial de ventas para DataTables
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/api/historial")
@login_required
def api_historial():
    fecha_inicio = request.args.get("fecha_inicio", "")
    fecha_fin    = request.args.get("fecha_fin", "")
    id_cliente   = request.args.get("id_cliente", "")

    query = db.session.query(
        Venta.IDVenta,
        Venta.fechaVenta,
        Venta.montoTotal,
        Venta.descuentoAplicado,
        Venta.impuesto,
        Cliente.nombre,
        Cliente.apellidoPaterno,
    ).join(Cliente, Venta.IDCliente == Cliente.IDCliente)

    if fecha_inicio:
        query = query.filter(Venta.fechaVenta >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Venta.fechaVenta <= fecha_fin)
    if id_cliente:
        try:
            query = query.filter(Venta.IDCliente == int(id_cliente))
        except ValueError:
            pass

    rows = query.order_by(Venta.fechaVenta.desc()).limit(500).all()

    data = [{
        "id_venta":   r.IDVenta,
        "fecha":      r.fechaVenta.strftime("%Y-%m-%d") if r.fechaVenta else "",
        "cliente":    f"{r.nombre} {r.apellidoPaterno or ''}".strip(),
        "monto":      float(r.montoTotal or 0),
        "descuento":  float(r.descuentoAplicado or 0),
        "impuesto":   float(r.impuesto or 0),
    } for r in rows]

    return jsonify({"data": data})


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Total de ventas del día
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/api/del_dia")
@login_required
def api_del_dia():
    fecha = request.args.get("fecha", date.today().isoformat())
    try:
        total = db.session.execute(
            text("SELECT fn_ventas_del_dia(:fecha)"),
            {"fecha": fecha}
        ).scalar()
        return jsonify({"fecha": fecha, "total": float(total or 0)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Nombre del cliente (búsqueda en tiempo real)
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/api/cliente/<int:id_cliente>")
@login_required
def api_cliente(id_cliente):
    try:
        nombre = db.session.execute(
            text("SELECT fn_nombre_cliente(:id)"),
            {"id": id_cliente}
        ).scalar()
        membresia = db.session.execute(
            text("SELECT fn_tiene_membresia_activa(:id)"),
            {"id": id_cliente}
        ).scalar()
        nivel = db.session.execute(
            text("SELECT fn_nivel_cliente(:id)"),
            {"id": id_cliente}
        ).scalar()
        return jsonify({
            "nombre":    nombre,
            "membresia": membresia,
            "nivel":     nivel,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Precio y stock del producto (verificación en tiempo real)
# ─────────────────────────────────────────────────────────────────────────────

@ventas_bp.route("/api/producto/<int:id_producto>")
@login_required
def api_producto(id_producto):
    try:
        precio = db.session.execute(
            text("SELECT fn_precio_producto(:id)"),
            {"id": id_producto}
        ).scalar()
        stock = db.session.execute(
            text("SELECT fn_stock_producto(:id)"),
            {"id": id_producto}
        ).scalar()
        tiene_stock = db.session.execute(
            text("SELECT fn_tiene_stock(:id)"),
            {"id": id_producto}
        ).scalar()

        prod = db.session.get(Producto, id_producto)
        return jsonify({
            "precio":      float(precio or 0),
            "stock":       int(stock or 0),
            "tiene_stock": tiene_stock,
            "nombre":      prod.nombreProducto if prod else "—",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404
