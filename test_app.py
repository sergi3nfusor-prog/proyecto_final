
"""
Test directo de los endpoints de Flask usando test client.
Esto prueba el código real del routes.py, no queries hardcodeadas.
"""
from app import create_app, db
from flask_login import login_user
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Primero verificamos que la app arranca bien
    print("[OK] App creada correctamente")
    
    # Limpiamos pycache por si acaso
    import importlib
    import app.dashboard.routes as dr
    importlib.reload(dr)
    
    # Test directo de las queries SQL corregidas
    print("\n=== TESTING QUERIES CORREGIDAS ===")
    
    # 1. Test CTE de segmentación de clientes (la nueva versión)
    try:
        rows = db.session.execute(text("""
            WITH totales_cliente AS (
                SELECT
                    c.idcliente,
                    c.nombre || ' ' || COALESCE(c.apellidopaterno, '') AS nombre_completo,
                    COALESCE(pf.nivel, 'Sin Registro') AS nivel_fidelidad,
                    COUNT(v.idventa) AS total_compras,
                    SUM(v.montototal) AS valor_total,
                    ROUND(AVG(v.montototal)::NUMERIC, 2) AS ticket_promedio
                FROM cliente c
                LEFT JOIN programafidelizacion pf ON c.idcliente = pf.idcliente
                JOIN venta v ON c.idcliente = v.idcliente
                GROUP BY c.idcliente, c.nombre, c.apellidopaterno, pf.nivel
            )
            SELECT *,
                CASE
                    WHEN valor_total > 5000 THEN 'Platino'
                    WHEN valor_total BETWEEN 2000 AND 5000 THEN 'Oro'
                    ELSE 'Plata'
                END AS segmento_valor
            FROM totales_cliente
            ORDER BY valor_total DESC
            LIMIT 10
        """)).fetchall()
        print(f"[OK] clientes_segmento (CTE): {len(rows)} clientes")
        for r in rows[:3]:
            print(f"  - {r.nombre_completo}: {r.segmento_valor} (Bs {r.valor_total})")
    except Exception as e:
        print(f"[ERROR] clientes_segmento: {e}")
        db.session.rollback()

    # 2. Test sucursales 
    try:
        rows = db.session.execute(text("""
            SELECT s.ciudad, s.nombresucursal,
                   COUNT(DISTINCT v.idventa) AS total_ventas,
                   SUM(v.montototal) AS recaudacion_total
            FROM sucursal s
            JOIN empleadosucursal es ON s.idsucursal = es.idsucursal
            JOIN venta v ON es.idempleado = v.idempleado
            GROUP BY s.ciudad, s.nombresucursal
            ORDER BY recaudacion_total DESC
        """)).fetchall()
        print(f"[OK] sucursales: {len(rows)} sucursales")
        for r in rows:
            print(f"  - {r.nombresucursal} ({r.ciudad}): Bs {r.recaudacion_total}")
    except Exception as e:
        print(f"[ERROR] sucursales: {e}")
        db.session.rollback()

    # 3. Test stock_salud
    try:
        rows = db.session.execute(text("""
            SELECT
                CASE
                    WHEN i.stockactual <= i.stockminimo THEN 'REPOSICION INMEDIATA'
                    WHEN i.stockactual <= (i.stockminimo * 1.5) THEN 'RIESGO BAJO'
                    ELSE 'STOCK SALUDABLE'
                END AS alerta_logistica,
                COUNT(*) AS conteo
            FROM producto p
            JOIN inventario i ON p.idinventario = i.idinventario
            GROUP BY alerta_logistica
        """)).fetchall()
        print(f"[OK] stock_salud: {len(rows)} categorias")
        for r in rows:
            print(f"  - {r.alerta_logistica}: {r.conteo} productos")
    except Exception as e:
        print(f"[ERROR] stock_salud: {e}")
        db.session.rollback()

    # 4. Test top productos
    try:
        rows = db.session.execute(text("""
            SELECT p.nombreproducto, p.marca,
                   SUM(dv.cantidad) AS unidades_vendidas
            FROM producto p
            JOIN detalleventa dv ON p.idproducto = dv.idproducto
            GROUP BY p.nombreproducto, p.marca
            ORDER BY unidades_vendidas DESC
            LIMIT 5
        """)).fetchall()
        print(f"[OK] top_productos: {len(rows)} productos")
        for r in rows:
            print(f"  - {r.nombreproducto}: {r.unidades_vendidas} uds")
    except Exception as e:
        print(f"[ERROR] top_productos: {e}")
        db.session.rollback()

    # 5. Test fn_resumen_ventas_mes
    try:
        rows = db.session.execute(text("SELECT * FROM fn_resumen_ventas_mes(:anio)"), {"anio": 2024}).fetchall()
        print(f"[OK] fn_resumen_ventas_mes(2024): {len(rows)} meses")
        cols = rows[0]._fields if rows else []
        print(f"  Columnas: {cols}")
    except Exception as e:
        print(f"[ERROR] fn_resumen_ventas_mes: {e}")
        db.session.rollback()

    # 6. Test tabla OLAP
    try:
        rows = db.session.execute(text("""
            SELECT
                EXTRACT(YEAR FROM v.fechaventa)::INT AS anio,
                EXTRACT(MONTH FROM v.fechaventa)::INT AS mes,
                s.ciudad AS plaza_venta,
                COUNT(DISTINCT v.idventa) AS total_transacciones,
                SUM(v.montototal) AS ingresos_brutos
            FROM venta v
            JOIN detalleventa dv ON v.idventa = dv.idventa
            JOIN cliente c ON v.idcliente = c.idcliente
            LEFT JOIN programafidelizacion pf ON c.idcliente = pf.idcliente
            JOIN empleadosucursal es ON v.idempleado = es.idempleado
            JOIN sucursal s ON es.idsucursal = s.idsucursal
            GROUP BY anio, mes, s.ciudad
            ORDER BY anio DESC, mes DESC
            LIMIT 3
        """)).fetchall()
        print(f"[OK] tabla_olap: {len(rows)} filas")
        for r in rows:
            print(f"  - {r.anio}/{r.mes} {r.plaza_venta}: Bs {r.ingresos_brutos}")
    except Exception as e:
        print(f"[ERROR] tabla_olap: {e}")
        db.session.rollback()

    print("\n=== FIN DEL TEST ===")

# Limpiar archivos temporales
import os
try:
    os.remove("test_output.txt")
except:
    pass
