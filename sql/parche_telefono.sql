-- =====================================================================
-- Parche: columna telefono en persona (y ajustes del esquema clinica)
-- Ejecutar en la base de datos del consultorio.
-- =====================================================================

-- 1. Numero de telefono de la persona (varchar(20), opcional)
--    La columna ya existe en la BD; este parche la garantiza por si la BD
--    de produccion no la tiene.
ALTER TABLE "clinica"."persona"
    ADD COLUMN IF NOT EXISTS "telefono" character varying(20);

-- 2. Asegurar las columnas/nivel exigidos por el esquema
ALTER TABLE "clinica"."antecedentes_salud"
    ADD COLUMN IF NOT EXISTS "valor" character varying(100);

ALTER TABLE "clinica"."enfermedad"
    ADD COLUMN IF NOT EXISTS "valor" character varying(20) NOT NULL DEFAULT '';

-- 3. Indices utiles
CREATE INDEX IF NOT EXISTS "idx_persona_nombre" ON "clinica"."persona" ("nombre_id");
CREATE INDEX IF NOT EXISTS "idx_persona_apellido" ON "clinica"."persona" ("apellido_id");
CREATE INDEX IF NOT EXISTS "idx_persona_direccion" ON "clinica"."persona" ("direccion_id");
