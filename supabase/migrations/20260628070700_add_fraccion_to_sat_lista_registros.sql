-- La excepcion de Fraccion VI (Art. 69 CFF: contribuyentes listados solo
-- por credito condonado no deben ser bloqueados) requiere almacenar la
-- fraccion que motivo la publicacion. Esta columna solo aplica para
-- list_type='art_69'; para los demas list_types queda NULL.
alter table sat_lista_registros
  add column fraccion text;
