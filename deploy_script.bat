@echo off
echo ==========================================
echo SCRIPT DE MIGRACIÓN Y DESPLIEGUE SEGURO
echo Proyecto: Tienda Deportiva
echo ==========================================
echo.

:: 1. Seguridad: No quemamos contraseñas aquí. 
:: Solicitamos de forma efímera para no guardar texto plano
set /p ORIGIN_DB="Introduce la URL de BD origen (Ej. de tu servidor local): "
set /p TARGET_DB="Introduce la URL de BD destino (Ej. en la Nube): "

echo.

:: 2. Migrando el Esquema (Estructura) usando el ORM de Flask
echo [1/3] Sincronizando estrucutura del ORM a la BD de destino...
set DATABASE_URL=%TARGET_DB%
flask db upgrade
if %errorlevel% neq 0 (
    echo [ERROR] Falló la creación de tablas con el ORM.
    exit /b %errorlevel%
)
echo [OK] Estructura creada exitosamente.

:: 3. Exportando Datos de Forma Segura (Dumping en memoria temporal)
echo [2/3] Generando respaldo temporal de datos desde BD Origen...
:: Con pg_dump extraemos solo los datos (-a), ignorando la estructura preexistente
pg_dump --dbname="%ORIGIN_DB%" -a -f "temp_data.sql"
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo extraer la información del origen.
    exit /b %errorlevel%
)
echo [OK] Datos copiados a archivo temporal.

:: 4. Importando Datos hacia la BD Destino
echo [3/3] Inyectando datos en BD Destino...
psql --dbname="%TARGET_DB%" -f "temp_data.sql"
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron inyectar los datos en el destino.
    exit /b %errorlevel%
)

:: 5. Limpiando archivos para mantener la seguridad (Borrar rastros)
echo [Limpieza] Eliminando archivo temporal...
del temp_data.sql

echo.
echo ==========================================
echo MIGRACION COMPLETADA DE FORMA SEGURA.
echo ==========================================
pause
