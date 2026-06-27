create extension if not exists pgcrypto;

create table expedientes (
  id uuid primary key default gen_random_uuid(),
  razon_social text not null,
  rfc text not null,
  domicilio_fiscal text,
  representante_legal text,
  status text not null default 'draft',
  decision text,
  score_total integer,
  needs_update_reason text,
  last_evaluated_at timestamptz,
  created_at timestamptz not null default now()
);

create table documentos (
  id uuid primary key default gen_random_uuid(),
  expediente_id uuid not null references expedientes(id) on delete cascade,
  doc_type text not null,
  entry_method text not null default 'uploaded',
  storage_path text,
  extraction_status text not null default 'pending',
  extracted_raw jsonb,
  fields jsonb,
  fecha_emision date,
  fecha_vencimiento date,
  created_at timestamptz not null default now()
);

create table socios (
  id uuid primary key default gen_random_uuid(),
  expediente_id uuid not null references expedientes(id) on delete cascade,
  nombre text,
  porcentaje_participacion numeric,
  es_beneficiario_controlador boolean not null default false,
  created_at timestamptz not null default now()
);

create table sat_lista_registros (
  id uuid primary key default gen_random_uuid(),
  list_type text not null,
  rfc text not null,
  razon_social text,
  art69b_substate text,
  situacion text,
  source_url text not null,
  import_batch_id uuid not null,
  created_at timestamptz not null default now()
);
create index idx_sat_lista_registros_list_rfc on sat_lista_registros (list_type, rfc);

create table sat_import_runs (
  id uuid primary key default gen_random_uuid(),
  list_type text not null,
  source_url text not null,
  status text not null,
  file_hash text,
  rows_imported integer,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table consultas_sat (
  id uuid primary key default gen_random_uuid(),
  expediente_id uuid not null references expedientes(id) on delete cascade,
  rfc_consultado text not null,
  list_type text not null,
  source_url text not null,
  found boolean not null default false,
  match_substate text,
  match_detail jsonb,
  consulted_at timestamptz not null default now()
);

create table evaluations (
  id uuid primary key default gen_random_uuid(),
  expediente_id uuid not null references expedientes(id) on delete cascade,
  score_total integer not null,
  decision text not null,
  critical_blocks jsonb not null default '[]'::jsonb,
  summary jsonb,
  created_at timestamptz not null default now()
);

create table factores_score (
  id uuid primary key default gen_random_uuid(),
  evaluation_id uuid not null references evaluations(id) on delete cascade,
  factor_code text not null,
  points integer not null,
  is_critical_block boolean not null default false,
  detail text,
  evidence jsonb,
  created_at timestamptz not null default now()
);

create table audit_log (
  id uuid primary key default gen_random_uuid(),
  expediente_id uuid references expedientes(id) on delete cascade,
  event_type text not null,
  payload jsonb,
  created_at timestamptz not null default now()
);

create table ai_call_cache (
  id uuid primary key default gen_random_uuid(),
  input_hash text not null unique,
  call_type text not null,
  schema_version text not null,
  result jsonb not null,
  retries integer not null default 0,
  created_at timestamptz not null default now()
);

-- Sin RLS: demo público sin autenticación (decisión consciente, ver CLAUDE.md).
-- El backend accede siempre con la service-role key, que bypassea RLS de todos modos.
