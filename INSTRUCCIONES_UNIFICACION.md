# Tienda Unificada Sport Zone

Este proyecto une:

- `tiendadeportivaweb`: página pública de la tienda.
- `tiendaanalitica`: login, ventas, inventario, dashboard y análisis.

## Rutas principales

- Página pública: `http://127.0.0.1:5000/`
- Login: `http://127.0.0.1:5000/login`
- Registro: `http://127.0.0.1:5000/registro`
- Ventas: `http://127.0.0.1:5000/ventas/registrar`
- Inventario: `http://127.0.0.1:5000/inventario/productos`
- Dashboard: `http://127.0.0.1:5000/dashboard/ejecutivo`

## Roles

| Rol | Acceso |
|---|---|
| usuario | Solo tienda pública |
| empleado | Ventas e inventario |
| gerente | Dashboard, ventas e inventario |
| admin | Acceso total |

## Códigos de acceso por defecto

| Rol | Código |
|---|---|
| empleado | `EMP-2026` |
| gerente | `GER-2026` |
| admin | `ADM-2026` |

El rol `usuario` no requiere código.

## Instalación

Desde PowerShell en la carpeta del proyecto:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuración de base de datos

Copiar `.env.example` a `.env` y ajustar la contraseña de PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg2://postgres:TU_PASSWORD@localhost:5432/tienda_deportiva
```

Luego ejecutar la migración de roles y bitácora sobre la base de datos:

```powershell
psql -U postgres -d tienda_deportiva -f migracion_unificada.sql
```

## Ejecutar

```powershell
python run.py
```

Abrir:

```text
http://127.0.0.1:5000/
```

## Nota técnica

La sección analítica depende de la base PostgreSQL original con sus tablas, funciones y procedimientos almacenados. Si la base no existe o no tiene las funciones `fn_*` / procedimientos `sp_*`, las páginas públicas pueden abrir, pero los módulos internos de ventas, inventario y dashboard pueden devolver errores.
