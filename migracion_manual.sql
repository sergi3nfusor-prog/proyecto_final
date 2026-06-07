-- ============================================================
-- MIGRACIÓN MANUAL — Tienda Deportiva
-- Ejecutar en psql conectado a la base de datos tienda_deportiva
-- ============================================================

-- 1. Ampliar el campo de contraseña para soportar hash bcrypt (255 chars)
ALTER TABLE usuarioempleado
    ALTER COLUMN contraseniaUsuario TYPE VARCHAR(255);

-- 2. Agregar columna de rol al usuario
ALTER TABLE usuarioempleado
    ADD COLUMN IF NOT EXISTS rol VARCHAR(20) NOT NULL DEFAULT 'vendedor';

-- Actualizar el CONSTRAINT para los roles válidos
ALTER TABLE usuarioempleado
    ADD CONSTRAINT chk_rol CHECK (rol IN ('admin', 'vendedor', 'almacen'));

-- 3. Crear tabla de bitácora de acceso (NUEVA)
CREATE TABLE IF NOT EXISTS bitacora_acceso (
    id          SERIAL PRIMARY KEY,
    usuario_id  INT REFERENCES usuarioempleado(IDUsuarioEmpleado) ON DELETE SET NULL,
    fecha_hora  TIMESTAMP DEFAULT NOW(),
    ip          VARCHAR(64),
    accion      VARCHAR(80),
    detalle     VARCHAR(255)
);

-- 4. Crear índices para mejorar consultas en bitácora
CREATE INDEX IF NOT EXISTS idx_bitacora_usuario
    ON bitacora_acceso(usuario_id);
CREATE INDEX IF NOT EXISTS idx_bitacora_fecha
    ON bitacora_acceso(fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_bitacora_accion
    ON bitacora_acceso(accion);

-- ============================================================
-- VERIFICACIÓN — ejecutar para confirmar los cambios
-- ============================================================
-- SELECT column_name, data_type, character_maximum_length
-- FROM information_schema.columns
-- WHERE table_name = 'usuarioempleado';
--
-- SELECT table_name FROM information_schema.tables
-- WHERE table_name = 'bitacora_acceso';
