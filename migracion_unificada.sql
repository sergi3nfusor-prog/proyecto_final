-- ============================================================
-- MIGRACIÓN — Tienda Unificada Sport Zone
-- Ejecutar conectado a PostgreSQL en la BD tienda_deportiva.
-- ============================================================

ALTER TABLE usuarioempleado
    ALTER COLUMN contraseniaUsuario TYPE VARCHAR(255);

ALTER TABLE usuarioempleado
    ADD COLUMN IF NOT EXISTS rol VARCHAR(20) NOT NULL DEFAULT 'usuario';

-- Compatibilidad con roles anteriores del proyecto analítico.
UPDATE usuarioempleado SET rol = 'empleado' WHERE rol IN ('vendedor', 'almacen');

ALTER TABLE usuarioempleado
    ALTER COLUMN rol SET DEFAULT 'usuario';

ALTER TABLE usuarioempleado
    DROP CONSTRAINT IF EXISTS chk_rol;

ALTER TABLE usuarioempleado
    ADD CONSTRAINT chk_rol CHECK (rol IN ('usuario', 'empleado', 'gerente', 'admin'));

CREATE TABLE IF NOT EXISTS bitacora_acceso (
    id          SERIAL PRIMARY KEY,
    usuario_id  INT REFERENCES usuarioempleado(IDUsuarioEmpleado) ON DELETE SET NULL,
    fecha_hora  TIMESTAMP DEFAULT NOW(),
    ip          VARCHAR(64),
    accion      VARCHAR(80),
    detalle     VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_bitacora_usuario ON bitacora_acceso(usuario_id);
CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON bitacora_acceso(fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_bitacora_accion ON bitacora_acceso(accion);

CREATE TABLE IF NOT EXISTS mensaje_contacto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    asunto VARCHAR(150),
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
