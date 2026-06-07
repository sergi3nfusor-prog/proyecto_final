from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import text

from app import db
from app.models import Producto, Inventario
from app.auth.routes import role_required

inventario_bp = Blueprint("inventario", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: Catálogo de productos
# ─────────────────────────────────────────────────────────────────────────────

@inventario_bp.route("/productos")
@login_required
@role_required("almacen", "admin")
def productos():
    return render_template("inventario/productos.html")


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: Alertas de stock bajo
# ─────────────────────────────────────────────────────────────────────────────

@inventario_bp.route("/alertas")
@login_required
@role_required("almacen", "admin")
def alertas():
    return render_template("inventario/alertas_stock.html")


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Lista de productos con estado de inventario
# ─────────────────────────────────────────────────────────────────────────────

@inventario_bp.route("/api/productos")
@login_required
def api_productos():
    marca    = request.args.get("marca", "")
    categoria = request.args.get("categoria", "")

    rows = (
        db.session.query(
            Producto.IDProducto,
            Producto.nombreProducto,
            Producto.marca,
            Producto.precio,
            Producto.talla,
            Producto.temporada,
            Inventario.stockActual,
            Inventario.stockMinimo,
            Inventario.stockMaximo,
        )
        .join(Inventario, Producto.IDInventario == Inventario.IDInventario)
        .filter(
            Producto.marca.ilike(f"%{marca}%") if marca else True,
        )
        .order_by(Inventario.stockActual.asc())
        .limit(500)
        .all()
    )

    data = []
    for r in rows:
        if r.stockActual <= r.stockMinimo:
            alerta = "REPOSICIÓN INMEDIATA"
        elif r.stockActual <= (r.stockMinimo * 1.5 if r.stockMinimo else 0):
            alerta = "RIESGO BAJO"
        else:
            alerta = "STOCK SALUDABLE"

        data.append({
            "id":       r.IDProducto,
            "nombre":   r.nombreProducto,
            "marca":    r.marca,
            "precio":   float(r.precio or 0),
            "talla":    r.talla,
            "temporada": r.temporada,
            "stock":    r.stockActual,
            "min":      r.stockMinimo,
            "max":      r.stockMaximo,
            "alerta":   alerta,
        })

    return jsonify({"data": data})


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Productos con stock bajo (función PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

@inventario_bp.route("/api/stock_bajo")
@login_required
def api_stock_bajo():
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_productos_stock_bajo()")
        ).fetchall()

        data = [{
            "id":      r.id_producto,
            "nombre":  r.nombre,
            "marca":   r.marca,
            "stock":   r.stock_actual,
            "minimo":  r.stock_minimo,
        } for r in rows]

        return jsonify({"data": data, "total": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API JSON: Valor monetario de un producto en inventario
# ─────────────────────────────────────────────────────────────────────────────

@inventario_bp.route("/api/valor_producto/<int:id_producto>")
@login_required
def api_valor_producto(id_producto):
    try:
        valor = db.session.execute(
            text("SELECT fn_valor_producto_inventario(:id)"),
            {"id": id_producto}
        ).scalar()
        return jsonify({"id_producto": id_producto, "valor_total": float(valor or 0)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
