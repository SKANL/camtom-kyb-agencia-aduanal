-- Requisito explicito de la seccion "Verificacion end-to-end" del plan
-- (linea 268): consultas_sat debe referenciar el import_run_id que la
-- origino, para trazabilidad de auditoria.
alter table consultas_sat
  add column import_run_id uuid references sat_import_runs(id);
