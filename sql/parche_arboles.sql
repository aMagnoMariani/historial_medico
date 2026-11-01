-- =====================================================================
-- Parche: estructura de ANCLA + TIPO para las tablas autorreferenciadas
-- Ejecutar en la base de datos del consultorio (esquema clinica).
--
-- Reglas que quedan aplicadas:
--   * id = 0 es la fila ancla "NINGUNO": nunca se borra ni se edita,
--     solo existe para que ninguna fila quede huérfana.
--   * `tipo` indica el nivel (1 = raíz del árbol).
--   * La columna del padre NUNCA es NULL: apunta a 0 (ancla) si es raíz
--     o al id del nivel inmediatamente superior.
--
-- Ejemplo de direccion:
--   id 0  NINGUNO      depid 0  tipo 0   <- ancla
--   id 1  MONAGAS      depid 0  tipo 1   <- Estado (raíz)
--   id 2  MATURIN      depid 1  tipo 2   <- Municipio
--   id 3  PALO NEGRO   depid 2  tipo 3   <- Parroquia
--
-- ORDEN IMPORTANTE: primero se quitan las llaves foráneas (si no, no se
-- puede insertar la ancla ni poner el padre en 0), se crea la ancla, se
-- normalizan los huérfanos y al final se recrean las llaves.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. QUITAR LAS LLAVES FORÁNEAS AUTOREFERENCIADAS
-- ---------------------------------------------------------------------
ALTER TABLE "clinica"."direccion"
    DROP CONSTRAINT IF EXISTS "direccion_divicion_politica_id_fk";

ALTER TABLE "clinica"."identificacion"
    DROP CONSTRAINT IF EXISTS "identificacion_descripcion_id_fk";

ALTER TABLE "clinica"."enfermedad"
    DROP CONSTRAINT IF EXISTS "enfermedad_enfermedad_id_fk";

-- ---------------------------------------------------------------------
-- 1. DIRECCION  (1=Estado, 2=Municipio, 3=Parroquia, 4=Calle/Sector)
-- ---------------------------------------------------------------------
ALTER TABLE "clinica"."direccion"
    ADD COLUMN IF NOT EXISTS "tipo" integer NOT NULL DEFAULT 0;

-- Fila ancla primero (así el 0 ya existe y no viola nada)
INSERT INTO "clinica"."direccion"
    ("id", "division_politica", "divicion_politica_id", "valor", "tipo")
VALUES (0, 'NINGUNO', 0, 'NINGUNO', 0)
ON CONFLICT ("id") DO UPDATE
  SET "division_politica" = 'NINGUNO',
      "divicion_politica_id" = 0,
      "valor"             = 'NINGUNO',
      "tipo"              = 0;

-- Los huérfanos pasan a apuntar a la ancla
UPDATE "clinica"."direccion"
   SET "divicion_politica_id" = 0
 WHERE "divicion_politica_id" IS NULL;

-- Detectar el nivel desde el texto que ya tenían los datos
UPDATE "clinica"."direccion"
   SET "tipo" = CASE
       WHEN "division_politica" ILIKE '%estado%'    THEN 1
       WHEN "division_politica" ILIKE '%municipio%' THEN 2
       WHEN "division_politica" ILIKE '%parroquia%' THEN 3
       WHEN "division_politica" ILIKE '%sector%'    THEN 4
       WHEN "division_politica" ILIKE '%calle%'     THEN 4
       WHEN "division_politica" ILIKE '%barrio%'    THEN 4
       WHEN "division_politica" ILIKE '%urbaniz%'   THEN 4
       -- si el padre es la ancla, es raíz del árbol
       WHEN "divicion_politica_id" = 0 THEN 1
       -- si no, un nivel más que su padre
       ELSE (SELECT COALESCE(p."tipo", 0) + 1 FROM "clinica"."direccion" p
             WHERE p."id" = "clinica"."direccion"."divicion_politica_id")
   END
 WHERE "id" <> 0;

-- Etiqueta legible del nivel
UPDATE "clinica"."direccion"
   SET "division_politica" = CASE "tipo"
       WHEN 1 THEN 'Estado'
       WHEN 2 THEN 'Municipio'
       WHEN 3 THEN 'Parroquia'
       WHEN 4 THEN 'Calle / Sector'
       ELSE 'NINGUNO'
   END
 WHERE "id" <> 0;

UPDATE "clinica"."direccion" SET "valor" = 'SIN NOMBRE'
 WHERE "valor" IS NULL OR "valor" = '';

ALTER TABLE "clinica"."direccion" ALTER COLUMN "divicion_politica_id" SET DEFAULT 0;
ALTER TABLE "clinica"."direccion" ALTER COLUMN "divicion_politica_id" SET NOT NULL;
ALTER TABLE "clinica"."direccion" ALTER COLUMN "tipo" SET DEFAULT 0;

-- Recrear la llave (ahora el 0 existe)
ALTER TABLE "clinica"."direccion"
    ADD CONSTRAINT "direccion_divicion_fkey"
    FOREIGN KEY ("divicion_politica_id")
    REFERENCES "clinica"."direccion" ("id");

-- ---------------------------------------------------------------------
-- 2. IDENTIFICACION  (1=Documento, 2=Subtipo)
-- ---------------------------------------------------------------------
ALTER TABLE "clinica"."identificacion"
    ADD COLUMN IF NOT EXISTS "tipo" integer NOT NULL DEFAULT 0;

INSERT INTO "clinica"."identificacion"
    ("id", "persona_id", "descripcion", "descripcion_id", "valor", "tipo")
VALUES (0, NULL, 'NINGUNO', 0, 'TIPO', 0)
ON CONFLICT ("id") DO UPDATE
  SET "descripcion" = 'NINGUNO', "descripcion_id" = 0, "tipo" = 0;

UPDATE "clinica"."identificacion"
   SET "descripcion_id" = 0
 WHERE "descripcion_id" IS NULL;

-- Los tipos de documento del catálogo no tienen persona -> nivel 1;
-- los de una persona concreta -> nivel 2.
UPDATE "clinica"."identificacion"
   SET "tipo" = CASE WHEN "persona_id" IS NULL THEN 1 ELSE 2 END
 WHERE "id" <> 0;

ALTER TABLE "clinica"."identificacion" ALTER COLUMN "descripcion_id" SET DEFAULT 0;
ALTER TABLE "clinica"."identificacion" ALTER COLUMN "descripcion_id" SET NOT NULL;

ALTER TABLE "clinica"."identificacion"
    ADD CONSTRAINT "identificacion_descripcion_fkey"
    FOREIGN KEY ("descripcion_id")
    REFERENCES "clinica"."identificacion" ("id");

-- ---------------------------------------------------------------------
-- 3. ENFERMEDAD  (1=Categoría, 2=Enfermedad)
--    La ancla necesita un diagnostico_id (la columna es NOT NULL),
--    se usa el diagnóstico comodín del catálogo.
-- ---------------------------------------------------------------------
ALTER TABLE "clinica"."enfermedad"
    ADD COLUMN IF NOT EXISTS "tipo" integer NOT NULL DEFAULT 0;

INSERT INTO "clinica"."enfermedad"
    ("id", "desc", "valor", "enfermedad_id", "diagnostico_id", "tipo")
SELECT 0, ARRAY['NINGUNO'], 'NINGUNO', 0, MIN("id"), 0
  FROM "clinica"."diagnostico"
ON CONFLICT ("id") DO UPDATE
  SET "enfermedad_id" = 0, "tipo" = 0;

UPDATE "clinica"."enfermedad"
   SET "enfermedad_id" = 0
 WHERE "enfermedad_id" IS NULL;

UPDATE "clinica"."enfermedad"
   SET "tipo" = CASE WHEN "enfermedad_id" = 0 THEN 1 ELSE 2 END
 WHERE "id" <> 0;

ALTER TABLE "clinica"."enfermedad" ALTER COLUMN "enfermedad_id" SET DEFAULT 0;
ALTER TABLE "clinica"."enfermedad" ALTER COLUMN "enfermedad_id" SET NOT NULL;

ALTER TABLE "clinica"."enfermedad"
    ADD CONSTRAINT "enfermedad_enfermedad_id_fk"
    FOREIGN KEY ("enfermedad_id")
    REFERENCES "clinica"."enfermedad" ("id");

-- ---------------------------------------------------------------------
-- 4. SINTOMAS  (1=Categoría, 2=Síntoma)
-- ---------------------------------------------------------------------
INSERT INTO "clinica"."sintomas"
    ("id", "desc", "depende", "tipo", "diagnostico_id")
SELECT 0, 'NINGUNO', 0, 0, MIN("id")
  FROM "clinica"."diagnostico"
ON CONFLICT ("id") DO UPDATE
  SET "depende" = 0, "tipo" = 0;

UPDATE "clinica"."sintomas"
   SET "depende" = 0
 WHERE "depende" IS NULL;

UPDATE "clinica"."sintomas"
   SET "tipo" = CASE WHEN "depende" = 0 THEN 1 ELSE 2 END
 WHERE "id" <> 0;

ALTER TABLE "clinica"."sintomas" ALTER COLUMN "depende" SET DEFAULT 0;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "depende" SET NOT NULL;
ALTER TABLE "clinica"."sintomas" ALTER COLUMN "tipo" SET DEFAULT 1;

ALTER TABLE "clinica"."sintomas"
    DROP CONSTRAINT IF EXISTS "sintomas";
ALTER TABLE "clinica"."sintomas"
    ADD CONSTRAINT "sintomas_depende_fkey"
    FOREIGN KEY ("depende")
    REFERENCES "clinica"."sintomas" ("id");

-- ---------------------------------------------------------------------
-- 5. ANTECEDENTES_SALUD  (1=Categoría, 2=Antecedente)
-- ---------------------------------------------------------------------
ALTER TABLE "clinica"."antecedentes_salud"
    ADD COLUMN IF NOT EXISTS "tipo" integer NOT NULL DEFAULT 2;

INSERT INTO "clinica"."antecedentes_salud"
    ("id", "descrip", "antecedente_salud_id", "valor", "paciente_id", "tipo")
VALUES (0, 'NINGUNO', 0, 'NINGUNO', 1, 0)
ON CONFLICT ("id") DO UPDATE
  SET "antecedente_salud_id" = 0, "tipo" = 0;

UPDATE "clinica"."antecedentes_salud"
   SET "antecedente_salud_id" = 0
 WHERE "antecedente_salud_id" IS NULL
    OR "antecedente_salud_id" NOT IN (SELECT "id" FROM "clinica"."antecedentes_salud");

UPDATE "clinica"."antecedentes_salud"
   SET "tipo" = CASE
       WHEN "descrip" ILIKE '%familiar%' THEN 1
       WHEN "descrip" ILIKE '%personal%' THEN 1
       ELSE 2
   END
 WHERE "id" <> 0 AND "antecedente_salud_id" = 0;

ALTER TABLE "clinica"."antecedentes_salud" ALTER COLUMN "antecedente_salud_id" SET DEFAULT 0;
ALTER TABLE "clinica"."antecedentes_salud" ALTER COLUMN "antecedente_salud_id" SET NOT NULL;

-- ---------------------------------------------------------------------
-- 6. ÍNDICES para recorrer los árboles rápido
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS "idx_direccion_tipo"   ON "clinica"."direccion" ("tipo");
CREATE INDEX IF NOT EXISTS "idx_direccion_padre"  ON "clinica"."direccion" ("divicion_politica_id");
CREATE INDEX IF NOT EXISTS "idx_identif_tipo"     ON "clinica"."identificacion" ("tipo");
CREATE INDEX IF NOT EXISTS "idx_identif_padre"    ON "clinica"."identificacion" ("descripcion_id");
CREATE INDEX IF NOT EXISTS "idx_enfermedad_tipo"  ON "clinica"."enfermedad" ("tipo");
CREATE INDEX IF NOT EXISTS "idx_enfermedad_padre" ON "clinica"."enfermedad" ("enfermedad_id");
CREATE INDEX IF NOT EXISTS "idx_sintomas_tipo"    ON "clinica"."sintomas" ("tipo");
CREATE INDEX IF NOT EXISTS "idx_sintomas_padre"   ON "clinica"."sintomas" ("depende");
CREATE INDEX IF NOT EXISTS "idx_antec_tipo"       ON "clinica"."antecedentes_salud" ("tipo");
CREATE INDEX IF NOT EXISTS "idx_antec_padre"      ON "clinica"."antecedentes_salud" ("antecedente_salud_id");
