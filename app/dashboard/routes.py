from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text, extract, func

from app import db
from app.models import Venta, Sucursal, Cliente, ProgramaFidelizacion, Producto, Inventario, DetalleVenta
from app.auth.routes import role_required

dashboard_bp = Blueprint("dashboard", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Extraer filtros de query params
# ─────────────────────────────────────────────────────────────────────────────

def _get_filters():
    return {
        "anio":     request.args.get("anio", ""),
        "ciudad":   request.args.get("ciudad", ""),
        "sucursal": request.args.get("sucursal", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VISTAS (solo admin)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/ejecutivo")
@login_required
@role_required("admin")
def ejecutivo():
    return render_template("dashboard/ejecutivo.html")


@dashboard_bp.route("/clientes")
@login_required
@role_required("admin")
def clientes():
    return render_template("dashboard/clientes.html")


@dashboard_bp.route("/productos")
@login_required
@role_required("admin")
def productos():
    return render_template("dashboard/productos.html")


# ─────────────────────────────────────────────────────────────────────────────
# API: Filtros disponibles para los selectores
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/filtros")
@login_required
def api_filtros():
    sucursales = db.session.query(Sucursal.nombreSucursal, Sucursal.ciudad).all()
    ciudades   = db.session.query(Sucursal.ciudad).distinct().all()
    anios      = (
        db.session.query(extract("year", Venta.fechaVenta).label("anio"))
        .distinct()
        .order_by(extract("year", Venta.fechaVenta).desc())
        .all()
    )

    return jsonify({
        "sucursales": [{"nombre": s.nombreSucursal, "ciudad": s.ciudad} for s in sucursales],
        "ciudades":   [c.ciudad for c in ciudades if c.ciudad],
        "anios":      [int(a.anio) for a in anios if a.anio],
    })


# ─────────────────────────────────────────────────────────────────────────────
# API: Ventas por mes (función PostgreSQL fn_resumen_ventas_mes)
# ─────────────────────────────────────────────────────────────────────────────

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


@dashboard_bp.route("/api/ventas_mes")
@login_required
def api_ventas_mes():
    filtros = _get_filters()
    anio    = int(filtros["anio"]) if filtros["anio"] else date.today().year

    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_resumen_ventas_mes(:anio)"),
            {"anio": anio}
        ).fetchall()

        mes_map = {r.mes: float(r.total_bs or 0) for r in rows}
        labels  = MESES
        data    = [mes_map.get(i + 1, 0) for i in range(12)]

        # KPIs complementarios
        total_general = db.session.execute(
            text("SELECT fn_total_general_ventas()")
        ).scalar()
        total_mes      = sum(data)
        transacciones  = db.session.query(func.count(Venta.IDVenta)).filter(
            extract("year", Venta.fechaVenta) == anio
        ).scalar() or 0
        ticket_prom    = round(total_mes / transacciones, 2) if transacciones else 0

        mes_actual = date.today().month
        total_descuentos = db.session.execute(
            text("SELECT fn_descuentos_mes(:mes, :anio)"),
            {"mes": mes_actual, "anio": anio}
        ).scalar()

        return jsonify({
            "labels":           labels,
            "data":             data,
            "anio":             anio,
            "total_mes":        round(total_mes, 2),
            "transacciones":    transacciones,
            "ticket_promedio":  ticket_prom,
            "total_descuentos": float(total_descuentos or 0),
            "total_historico":  float(total_general or 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Segmentación de clientes (Cubo de Clientes)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/clientes_segmento")
@login_required
def api_clientes_segmento():
    try:
        # CTE: calcular totales por cliente, luego segmentar en la capa externa
        rows_by_cliente = db.session.execute(text("""
            WITH totales_cliente AS (
                SELECT
                    c.idcliente,
                    c.nombre || ' ' || COALESCE(c.apellidopaterno, '') AS nombre_completo,
                    COALESCE(pf.nivel, 'Sin Registro') AS nivel_fidelidad,
                    COUNT(v.idventa)                       AS total_compras,
                    SUM(v.montototal)                      AS valor_total,
                    ROUND(AVG(v.montototal)::NUMERIC, 2)   AS ticket_promedio
                FROM cliente c
                LEFT JOIN programafidelizacion pf ON c.idcliente = pf.idcliente
                JOIN venta v ON c.idcliente = v.idcliente
                GROUP BY c.idcliente, c.nombre, c.apellidopaterno, pf.nivel
            )
            SELECT *,
                CASE
                    WHEN valor_total > 5000              THEN 'Platino'
                    WHEN valor_total BETWEEN 2000 AND 5000 THEN 'Oro'
                    ELSE 'Plata'
                END AS segmento_valor
            FROM totales_cliente
            ORDER BY valor_total DESC
            LIMIT 100
        """)).fetchall()

        # Conteo por segmento
        segmentos: dict = {}
        for r in rows_by_cliente:
            seg = r.segmento_valor
            segmentos[seg] = segmentos.get(seg, 0) + 1

        # Top 10 clientes
        top10 = [{
            "nombre":         r.nombre_completo,
            "nivel":          r.nivel_fidelidad,
            "total_compras":  r.total_compras,
            "valor_total":    float(r.valor_total or 0),
            "ticket_promedio": float(r.ticket_promedio or 0),
            "segmento":       r.segmento_valor,
        } for r in rows_by_cliente[:10]]

        # KPIs
        total_clientes = db.session.query(func.count(func.distinct(Venta.IDCliente))).scalar() or 0

        return jsonify({
            "segmentos": {
                "labels": list(segmentos.keys()),
                "data":   list(segmentos.values()),
            },
            "top10":           top10,
            "total_clientes":  total_clientes,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Recaudación por sucursal (Cubo de Sucursales)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/sucursales")
@login_required
def api_sucursales():
    filtros = _get_filters()
    try:
        sql = text("""
            SELECT
                s.ciudad,
                s.nombresucursal,
                COUNT(DISTINCT v.idventa)      AS total_ventas,
                COUNT(DISTINCT es.idempleado)  AS nro_empleados,
                SUM(v.montototal)              AS recaudacion_total,
                ROUND(SUM(v.montototal)::NUMERIC /
                    NULLIF(COUNT(DISTINCT es.idempleado), 0), 2) AS productividad_por_empleado
            FROM sucursal s
            JOIN empleadosucursal es ON s.idsucursal = es.idsucursal
            JOIN venta v             ON es.idempleado = v.idempleado
            WHERE (:ciudad = '' OR s.ciudad = :ciudad)
            GROUP BY s.ciudad, s.nombresucursal
            ORDER BY recaudacion_total DESC
        """)
        rows = db.session.execute(sql, {"ciudad": filtros["ciudad"]}).fetchall()

        return jsonify({
            "labels": [r.nombresucursal for r in rows],
            "recaudacion": [float(r.recaudacion_total or 0) for r in rows],
            "productividad": [float(r.productividad_por_empleado or 0) for r in rows],
            "nro_empleados": [int(r.nro_empleados) for r in rows],
            "ciudades": [r.ciudad for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Salud del stock (Cubo de Inventario)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/stock_salud")
@login_required
def api_stock_salud():
    try:
        rows = db.session.execute(text("""
            SELECT
                CASE
                    WHEN i.stockactual <= i.stockminimo THEN 'REPOSICIÓN INMEDIATA'
                    WHEN i.stockactual <= (i.stockminimo * 1.5) THEN 'RIESGO BAJO'
                    ELSE 'STOCK SALUDABLE'
                END AS alerta_logistica,
                COUNT(*) AS conteo
            FROM producto p
            JOIN inventario i ON p.idinventario = i.idinventario
            GROUP BY alerta_logistica
            ORDER BY conteo DESC
        """)).fetchall()

        return jsonify({
            "labels": [r.alerta_logistica for r in rows],
            "data":   [int(r.conteo) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Tabla OLAP — Inteligencia de Negocio 360°
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/tabla_olap")
@login_required
def api_tabla_olap():
    filtros = _get_filters()
    try:
        sql = text("""
            SELECT
                EXTRACT(YEAR  FROM v.fechaventa)::INT  AS anio,
                EXTRACT(MONTH FROM v.fechaventa)::INT  AS mes,
                s.ciudad                               AS plaza_venta,
                COALESCE(pf.nivel, 'No Miembro')       AS perfil_fidelidad,
                COUNT(DISTINCT v.idventa)              AS total_transacciones,
                SUM(dv.cantidad)                       AS volumen_articulos,
                ROUND(SUM(v.montototal)::NUMERIC, 2)   AS ingresos_brutos,
                ROUND(SUM(v.descuentoaplicado)::NUMERIC, 2) AS ahorro_clientes,
                ROUND(SUM(v.montototal - v.descuentoaplicado)::NUMERIC, 2) AS ingresos_netos,
                ROUND((SUM(v.descuentoaplicado) /
                    NULLIF(SUM(v.montototal), 0)) * 100, 2) || '%%' AS impacto_promocional
            FROM venta v
            JOIN detalleventa dv     ON v.idventa    = dv.idventa
            JOIN cliente c           ON v.idcliente  = c.idcliente
            LEFT JOIN programafidelizacion pf ON c.idcliente = pf.idcliente
            JOIN empleadosucursal es ON v.idempleado = es.idempleado
            JOIN sucursal s          ON es.idsucursal = s.idsucursal
            WHERE
                (:anio    = '' OR EXTRACT(YEAR  FROM v.fechaventa)::TEXT = :anio)
                AND (:ciudad  = '' OR s.ciudad = :ciudad)
                AND (:sucursal = '' OR s.nombresucursal = :sucursal)
            GROUP BY anio, mes, s.ciudad, perfil_fidelidad
            ORDER BY anio DESC, mes DESC, ingresos_netos DESC
            LIMIT 500
        """)
        rows = db.session.execute(sql, {
            "anio":     filtros["anio"],
            "ciudad":   filtros["ciudad"],
            "sucursal": filtros["sucursal"],
        }).fetchall()

        columns = [
            "Año", "Mes", "Plaza de Venta", "Perfil Fidelidad",
            "Transacciones", "Volumen Artículos",
            "Ingresos Brutos (Bs)", "Ahorro Clientes (Bs)",
            "Ingresos Netos (Bs)", "Impacto Promocional"
        ]
        data = [[
            r.anio, r.mes, r.plaza_venta, r.perfil_fidelidad,
            r.total_transacciones, int(r.volumen_articulos or 0),
            float(r.ingresos_brutos or 0), float(r.ahorro_clientes or 0),
            float(r.ingresos_netos or 0), r.impacto_promocional or "0.00%"
        ] for r in rows]

        return jsonify({"columns": columns, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Dashboard de Productos
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/productos_dashboard")
@login_required
def api_productos_dashboard():
    try:
        # Unidades vendidas por producto (TOP 10)
        top_productos = db.session.execute(text("""
            SELECT p.nombreproducto, p.marca,
                   SUM(dv.cantidad) AS unidades_vendidas,
                   ROUND(SUM(dv.subtotal)::NUMERIC, 2) AS ingreso_total
            FROM producto p
            JOIN detalleventa dv ON p.idproducto = dv.idproducto
            GROUP BY p.nombreproducto, p.marca
            ORDER BY unidades_vendidas DESC
            LIMIT 10
        """)).fetchall()

        # Valor total en inventario
        valor_total = db.session.execute(text("""
            SELECT SUM(p.precio * i.stockactual)
            FROM producto p JOIN inventario i ON p.idinventario = i.idinventario
        """)).scalar()

        # Productos en alerta
        en_alerta = db.session.execute(text("""
            SELECT COUNT(*) FROM producto p
            JOIN inventario i ON p.idinventario = i.idinventario
            WHERE i.stockactual <= i.stockminimo
        """)).scalar()

        return jsonify({
            "top_productos": [{
                "nombre": r.nombreproducto,
                "marca":  r.marca,
                "unidades": int(r.unidades_vendidas or 0),
                "ingreso": float(r.ingreso_total or 0),
            } for r in top_productos],
            "valor_total_inventario": float(valor_total or 0),
            "productos_en_alerta":   int(en_alerta or 0),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
