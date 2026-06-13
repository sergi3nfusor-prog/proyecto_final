from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text, extract, func

from app import db
from app.models import Venta, Sucursal, Cliente, ProgramaFidelizacion, Producto, Inventario, DetalleVenta, Categoria
from app.auth.routes import role_required

dashboard_bp = Blueprint("dashboard", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Extraer filtros de query params
# ─────────────────────────────────────────────────────────────────────────────

def _get_filters():
    return {
        "anio":     request.args.get("anio", ""),
        "mes":      request.args.get("mes", ""),
        "ciudad":   request.args.get("ciudad", ""),
        "sucursal": request.args.get("sucursal", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VISTAS (solo admin)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/ejecutivo")
@login_required
@role_required("gerente", "admin")
def ejecutivo():
    return render_template("dashboard/ejecutivo.html")


@dashboard_bp.route("/clientes")
@login_required
@role_required("gerente", "admin")
def clientes():
    return render_template("dashboard/clientes.html")


@dashboard_bp.route("/productos")
@login_required
@role_required("gerente", "admin")
def productos():
    return render_template("dashboard/productos.html")


# ─────────────────────────────────────────────────────────────────────────────
# API: Filtros disponibles para los selectores
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/filtros")
@login_required
@role_required("gerente", "admin")
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
@role_required("gerente", "admin")
def api_ventas_mes():
    filtros = _get_filters()
    anio_str = filtros["anio"]
    mes_str  = filtros["mes"]
    anio = int(anio_str) if anio_str and str(anio_str).isdigit() else date.today().year
    mes  = int(mes_str) if mes_str and str(mes_str).isdigit() else None
    if mes is not None and not (1 <= mes <= 12):
        mes = None

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
        total_mes = data[mes - 1] if mes else sum(data)
        q_trans = db.session.query(func.count(Venta.IDVenta)).filter(
            extract("year", Venta.fechaVenta) == anio
        )
        if mes:
            q_trans = q_trans.filter(extract("month", Venta.fechaVenta) == mes)
        transacciones = q_trans.scalar() or 0
        ticket_prom    = round(total_mes / transacciones, 2) if transacciones else 0

        mes_para_descuentos = mes if mes else date.today().month
        total_descuentos = db.session.execute(
            text("SELECT fn_descuentos_mes(:mes, :anio)"),
            {"mes": mes_para_descuentos, "anio": anio}
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
@role_required("gerente", "admin")
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
@role_required("gerente", "admin")
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
            LEFT JOIN venta v        ON es.idempleado = v.idempleado
            WHERE (:ciudad = '' OR s.ciudad  = :ciudad)
              AND (:anio   = '' OR EXTRACT(YEAR  FROM v.fechaventa)::text = :anio)
              AND (:mes    = '' OR EXTRACT(MONTH FROM v.fechaventa)::text = :mes)
            GROUP BY s.ciudad, s.nombresucursal
            ORDER BY recaudacion_total DESC
        """)
        rows = db.session.execute(sql, {
            "ciudad": filtros["ciudad"],
            "anio":   filtros["anio"],
            "mes":    filtros["mes"]
        }).fetchall()

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
@role_required("gerente", "admin")
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
@role_required("gerente", "admin")
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
                ROUND(SUM(dv.subtotal)::NUMERIC, 2)   AS ingresos_brutos,
                ROUND(SUM(dv.descuento)::NUMERIC, 2) AS ahorro_clientes,
                ROUND(SUM(dv.subtotal - dv.descuento)::NUMERIC, 2) AS ingresos_netos,
                ROUND((SUM(dv.descuento) /
                    NULLIF(SUM(dv.subtotal), 0)) * 100, 2) || '%%' AS impacto_promocional
            FROM venta v
            JOIN detalleventa dv     ON v.idventa    = dv.idventa
            JOIN cliente c           ON v.idcliente  = c.idcliente
            LEFT JOIN programafidelizacion pf ON c.idcliente = pf.idcliente
            JOIN empleadosucursal es ON v.idempleado = es.idempleado
            JOIN sucursal s          ON es.idsucursal = s.idsucursal
            WHERE
                (:anio    = '' OR EXTRACT(YEAR  FROM v.fechaventa)::INT::TEXT = :anio)
                AND (:mes  = '' OR EXTRACT(MONTH FROM v.fechaventa)::INT::TEXT = :mes)
                AND (:ciudad  = '' OR s.ciudad = :ciudad)
                AND (:sucursal = '' OR s.nombresucursal = :sucursal)
            GROUP BY anio, mes, s.ciudad, perfil_fidelidad
            ORDER BY anio DESC, mes DESC, ingresos_netos DESC
            LIMIT 500
        """)
        rows = db.session.execute(sql, {
            "anio":     filtros["anio"],
            "mes":      filtros["mes"],
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
@role_required("gerente", "admin")
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


# ─────────────────────────────────────────────────────────────────────────────
# API: Ventas por marca (bar chart)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/ventas_marca")
@login_required
@role_required("gerente", "admin")
def api_ventas_marca():
    filtros = _get_filters()
    anio = int(filtros["anio"]) if filtros["anio"] else None
    mes  = int(filtros["mes"])  if filtros["mes"]  else None
    try:
        q = db.session.query(
            Producto.marca.label("marca"),
            func.sum(DetalleVenta.subtotal).label("total")
        ).join(DetalleVenta, DetalleVenta.IDProducto == Producto.IDProducto
        ).join(Venta, Venta.IDVenta == DetalleVenta.IDVenta)
        if anio:
            q = q.filter(extract("year", Venta.fechaVenta) == anio)
        if mes:
            q = q.filter(extract("month", Venta.fechaVenta) == mes)
        q = q.filter(Producto.marca.isnot(None)).group_by(Producto.marca).order_by(func.sum(DetalleVenta.subtotal).desc()).limit(8)
        rows = q.all()
        return jsonify({
            "labels": [r.marca for r in rows],
            "data":   [float(r.total or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Evolución de clientes nuevos por mes (line chart)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/clientes_nuevos_mes")
@login_required
@role_required("gerente", "admin")
def api_clientes_nuevos_mes():
    filtros = _get_filters()
    anio = int(filtros["anio"]) if filtros["anio"] else None
    try:
        subq = (
            db.session.query(
                Venta.IDCliente,
                func.min(Venta.fechaVenta).label("primera_compra")
            )
            .group_by(Venta.IDCliente)
            .subquery()
        )
        q = (
            db.session.query(
                extract("month", subq.c.primera_compra).label("mes"),
                func.count(subq.c.IDCliente).label("nuevos")
            )
        )
        if anio:
            q = q.filter(extract("year", subq.c.primera_compra) == anio)
        rows = (
            q.group_by(extract("month", subq.c.primera_compra))
            .order_by(extract("month", subq.c.primera_compra))
            .all()
        )
        mes_map = {int(r.mes): int(r.nuevos) for r in rows}
        return jsonify({
            "labels": MESES,
            "data":   [mes_map.get(i + 1, 0) for i in range(12)],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Compras por género de cliente (Dashboard Clientes — gráfico 3)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/compras_genero")
@login_required
@role_required("gerente", "admin")
def api_compras_genero():
    filtros = _get_filters()
    try:
        q = (
            db.session.query(
                Cliente.genero.label("genero"),
                func.count(Venta.IDVenta).label("total_compras"),
                func.sum(Venta.montoTotal).label("monto_total")
            )
            .join(Venta, Venta.IDCliente == Cliente.IDCliente)
            .filter(Cliente.genero.isnot(None))
        )
        if filtros["anio"]:
            q = q.filter(extract("year", Venta.fechaVenta) == int(filtros["anio"]))
        rows = q.group_by(Cliente.genero).order_by(func.count(Venta.IDVenta).desc()).all()
        return jsonify({
            "labels": [r.genero for r in rows],
            "compras": [int(r.total_compras) for r in rows],
            "montos":  [float(r.monto_total or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Actividad de clientes por mes — primeras compras (Dashboard Clientes — gráfico 4)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/actividad_clientes_mes")
@login_required
@role_required("gerente", "admin")
def api_actividad_clientes_mes():
    filtros = _get_filters()
    anio = int(filtros["anio"]) if filtros["anio"] else None
    try:
        q = (
            db.session.query(
                extract("month", Venta.fechaVenta).label("mes"),
                func.count(func.distinct(Venta.IDCliente)).label("clientes_activos"),
                func.count(Venta.IDVenta).label("total_ventas")
            )
        )
        if anio:
            q = q.filter(extract("year", Venta.fechaVenta) == anio)
            
        rows = (
            q.group_by(extract("month", Venta.fechaVenta))
            .order_by(extract("month", Venta.fechaVenta))
            .all()
        )
        mes_map_clientes = {int(r.mes): int(r.clientes_activos) for r in rows}
        mes_map_ventas   = {int(r.mes): int(r.total_ventas) for r in rows}
        return jsonify({
            "labels":          MESES,
            "clientes_activos": [mes_map_clientes.get(i + 1, 0) for i in range(12)],
            "total_ventas":     [mes_map_ventas.get(i + 1, 0) for i in range(12)],
            "anio":             anio,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ingresos por categoría de producto (Dashboard Productos — gráfico 3)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ingresos_categoria")
@login_required
@role_required("gerente", "admin")
def api_ingresos_categoria():
    try:
        rows = (
            db.session.query(
                Categoria.nombreCategoria.label("categoria"),
                func.sum(DetalleVenta.subtotal).label("ingresos"),
                func.sum(DetalleVenta.cantidad).label("unidades")
            )
            .join(Producto, Producto.IDProducto == Categoria.IDProducto)
            .join(DetalleVenta, DetalleVenta.IDProducto == Producto.IDProducto)
            .filter(Categoria.nombreCategoria.isnot(None))
            .group_by(Categoria.nombreCategoria)
            .order_by(func.sum(DetalleVenta.subtotal).desc())
            .limit(8)
            .all()
        )
        return jsonify({
            "labels":   [r.categoria for r in rows],
            "ingresos": [float(r.ingresos or 0) for r in rows],
            "unidades": [int(r.unidades or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ingresos por temporada de producto (Dashboard Productos — gráfico 4)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ventas_temporada")
@login_required
@role_required("gerente", "admin")
def api_ventas_temporada():
    try:
        rows = (
            db.session.query(
                Producto.temporada.label("temporada"),
                func.sum(DetalleVenta.subtotal).label("ingresos"),
                func.count(func.distinct(Venta.IDVenta)).label("transacciones")
            )
            .join(DetalleVenta, DetalleVenta.IDProducto == Producto.IDProducto)
            .join(Venta, Venta.IDVenta == DetalleVenta.IDVenta)
            .filter(Producto.temporada.isnot(None))
            .group_by(Producto.temporada)
            .order_by(func.sum(DetalleVenta.subtotal).desc())
            .all()
        )
        return jsonify({
            "labels":        [r.temporada for r in rows],
            "ingresos":      [float(r.ingresos or 0) for r in rows],
            "transacciones": [int(r.transacciones) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ingresos por Nivel de Fidelidad (Dashboard Clientes — gráfico 5)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ingresos_fidelidad")
@login_required
@role_required("gerente", "admin")
def api_ingresos_fidelidad():
    filtros = _get_filters()
    try:
        q = (
            db.session.query(
                func.coalesce(ProgramaFidelizacion.nivel, 'Sin Registro').label("nivel"),
                func.sum(Venta.montoTotal).label("ingresos")
            )
            .select_from(Venta)
            .join(Cliente, Cliente.IDCliente == Venta.IDCliente)
            .outerjoin(ProgramaFidelizacion, ProgramaFidelizacion.IDCliente == Cliente.IDCliente)
        )
        if filtros["anio"]:
            q = q.filter(extract("year", Venta.fechaVenta) == int(filtros["anio"]))
        rows = q.group_by("nivel").order_by(func.sum(Venta.montoTotal).desc()).all()
        return jsonify({
            "labels": [r.nivel for r in rows],
            "ingresos": [float(r.ingresos or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ticket Promedio por Mes (Dashboard Clientes — gráfico 6)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ticket_promedio_mes")
@login_required
@role_required("gerente", "admin")
def api_ticket_promedio_mes():
    filtros = _get_filters()
    anio = int(filtros["anio"]) if filtros["anio"] else None
    try:
        q = db.session.query(
            extract("month", Venta.fechaVenta).label("mes"),
            func.avg(Venta.montoTotal).label("ticket_promedio")
        )
        if anio:
            q = q.filter(extract("year", Venta.fechaVenta) == anio)

        rows = (
            q.group_by(extract("month", Venta.fechaVenta))
            .order_by(extract("month", Venta.fechaVenta))
            .all()
        )
        mes_map = {int(r.mes): float(r.ticket_promedio or 0) for r in rows}
        return jsonify({
            "labels": MESES,
            "data": [mes_map.get(i + 1, 0) for i in range(12)],
            "anio": anio,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ingresos por Material (Dashboard Productos — gráfico 5)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ingresos_material")
@login_required
@role_required("gerente", "admin")
def api_ingresos_material():
    try:
        rows = (
            db.session.query(
                Producto.material.label("material"),
                func.sum(DetalleVenta.subtotal).label("ingresos")
            )
            .join(DetalleVenta, DetalleVenta.IDProducto == Producto.IDProducto)
            .filter(Producto.material.isnot(None))
            .filter(Producto.material != "")
            .group_by(Producto.material)
            .order_by(func.sum(DetalleVenta.subtotal).desc())
            .limit(6)
            .all()
        )
        return jsonify({
            "labels": [r.material for r in rows],
            "ingresos": [float(r.ingresos or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Ventas por Talla (Dashboard Productos — gráfico 6)
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_bp.route("/api/ventas_talla")
@login_required
@role_required("gerente", "admin")
def api_ventas_talla():
    try:
        rows = (
            db.session.query(
                Producto.talla.label("talla"),
                func.sum(DetalleVenta.cantidad).label("unidades")
            )
            .join(DetalleVenta, DetalleVenta.IDProducto == Producto.IDProducto)
            .filter(Producto.talla.isnot(None))
            .filter(Producto.talla != "")
            .group_by(Producto.talla)
            .order_by(func.sum(DetalleVenta.cantidad).desc())
            .limit(10)
            .all()
        )
        return jsonify({
            "labels": [r.talla for r in rows],
            "unidades": [int(r.unidades or 0) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
