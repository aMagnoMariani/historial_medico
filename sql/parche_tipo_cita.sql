-- =====================================================================
-- Parche: tipo de cita (primera vez, rutina, seguimiento, control, emergencia)
-- Ejecutar en la base de datos del consultorio (esquema clinica).
-- =====================================================================

-- 1. Columna tipo_cita en la tabla cita (varchar(20), opcional)
--    La columna puede que ya exista; este parche la garantiza.
ALTER TABLE "clinica"."cita"
    ADD COLUMN IF NOT EXISTS "tipo_cita" character varying(20);

-- 2. Valores permitidos por el sistema.
--    (No se agrega un CHECK constraint para no bloquear valores nuevos
--     que se definan después desde el modelo de Django.)
COMMENT ON COLUMN "clinica"."cita"."tipo_cita" IS
    'Motivo de la cita: PRIMERA, RUTINA, SEGUIMIENTO, CONTROL, EMERGENCIA';

-- 3. Citas antiguas sin tipo: quedan marcadas como RUTINA
--    (valor más neutro; cámbialo si prefieres otro).
UPDATE "clinica"."cita"
   SET "tipo_cita" = 'RUTINA'
 WHERE "tipo_cita" IS NULL OR "tipo_cita" = '';

-- 4. Índice para los reportes que filtran por tipo de cita
CREATE INDEX IF NOT EXISTS "idx_cita_tipo" ON "clinica"."cita" ("tipo_cita");
