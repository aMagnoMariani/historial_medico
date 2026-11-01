-- =====================================================================
-- Parche para alinear la BD real con el esquema SQL definido.
-- Ejecutar en la base de datos del consultorio (esquema clinica).
-- =====================================================================

-- 1. enfermedad.valor  (varchar(20) NOT NULL segun el esquema)
--    La columna NO existia en la BD: se agrega con valor por defecto
--    para no romper las filas ya registradas.
ALTER TABLE "clinica"."enfermedad"
    ADD COLUMN IF NOT EXISTS "valor" character varying(20);

UPDATE "clinica"."enfermedad"
   SET "valor" = COALESCE("desc"[1], 'S/N')
 WHERE "valor" IS NULL OR "valor" = '';

ALTER TABLE "clinica"."enfermedad"
    ALTER COLUMN "valor" SET NOT NULL;

-- 2. sintomas.depende / sintomas.tipo  (NOT NULL segun el esquema)
UPDATE "clinica"."sintomas" SET "depende" = 0 WHERE "depende" IS NULL;
UPDATE "clinica"."sintomas" SET "tipo"    = 1 WHERE "tipo"    IS NULL;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "depende" SET DEFAULT 0;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "tipo"    SET DEFAULT 1;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "depende" SET NOT NULL;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "tipo"    SET NOT NULL;

-- 3. diagnostico.descr / diagnostico.conducta_id  (NOT NULL segun el esquema)
UPDATE "clinica"."diagnostico" SET "descr" = '' WHERE "descr" IS NULL;
ALTER TABLE "clinica"."diagnostico" ALTER COLUMN "descr" SET DEFAULT '';
ALTER TABLE "clinica"."diagnostico" ALTER COLUMN "descr" SET NOT NULL;

-- 4. conducta.descripcion  (texto libre para observaciones de la conducta)
--    La columna ya existe en la BD; se garantiza el indice de busqueda.
CREATE INDEX IF NOT EXISTS "idx_conducta_descripcion"
    ON "clinica"."conducta" ("descripcion");
