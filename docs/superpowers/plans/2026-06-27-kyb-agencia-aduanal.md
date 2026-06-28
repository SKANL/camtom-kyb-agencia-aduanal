# KYB para Agencia Aduanal — Camtom Technical Challenge

## Contexto

Prueba técnica de 48h naturales para el puesto de Software Engineer en Camtom (recibida viernes 26/06/2026 4:45pm — **deadline domingo 28/06/2026 4:45pm**). El resultado pesa directamente en una decisión de contratación y negociación salarial, así que el objetivo no es solo "que funcione" sino demostrar criterio de ingeniería: arquitectura limpia (SOLID/KISS, separación de responsabilidades real), motor de riesgo determinístico/explicable/testeable (el propio brief lo marca como "el punto más importante de la prueba"), uso real de datos públicos del SAT (sin mocks en esa parte específica), uso genuino de IA tratada como componente NO confiable dentro de un sistema confiable ("harness engineering": el LLM nunca decide, solo informa a un motor determinístico que sí decide), y alineación visible con el stack real de Camtom (React/TypeScript + FastAPI/Python + LangChain).

Entrega esperada como respuesta al correo de Pedro Ríos (CTO): URL pública desplegada, repo público de GitHub, y transcript de esta conversación en JSONL/Markdown.

## Decisiones de arquitectura (no rediscutir en la implementación)

- **Dos servicios separados, un monorepo**: `frontend/` (Next.js) y `backend/` (FastAPI), cada uno deployado como su propio proyecto de Vercel (Vercel soporta monorepos con "Root Directory" por proyecto — confirmado, patrón estándar). Comunicación exclusivamente vía API REST del backend; el frontend no toca Supabase directamente.
- **Backend = FastAPI (Python)**: dueño único de toda la lógica de negocio, acceso a datos, IA, ETL del SAT y el motor de reglas. Confirmado vía Context7 que Vercel soporta FastAPI nativamente (Python runtime, detecta el `app` ASGI). Dependencias gestionadas con **uv** (`pyproject.toml` + `uv.lock` para desarrollo; `requirements.txt` generado vía `uv export` para el build de Vercel, que espera ese formato).
- **Frontend = Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Zustand**: solo presentación. Llama al backend vía un cliente API tipado. Las subidas de archivos van directo a Supabase Storage por signed URL (el backend emite la URL firmada; el frontend nunca tiene la service-role key).
- **Base de datos**: Supabase (Postgres + Storage), accedida **únicamente** desde el backend.
- **IA**: LangChain (Python, ecosistema original, más maduro que el puerto JS) + `langchain-groq`. Cerebras descartado (sin soporte confirmado de structured output). Groq confirmado para tool calling/structured output, **NO soporta image input** (verificado en la página específica de la integración, no en la tabla genérica que sí lo afirmaba incorrectamente — corrección propia documentada).
- **Extracción automática completa desde PDF** (decisión del usuario, riesgo asumido conscientemente) con **revisión/edición humana obligatoria** antes de persistir cualquier dato extraído — ningún dato de IA llega al motor de scoring sin confirmación humana.
- **Capa de Harness obligatoria** alrededor de toda llamada a IA (ver sección dedicada) — no es opcional ni "si hay tiempo".
- **OCR**: `pytesseract` + extracción de texto nativo como primer intento; fallback a OCR si no hay capa de texto. Riesgo de binario de Tesseract en serverless de Vercel — **spike obligatorio en fase 1**, con fallback documentado a "requiere PDF con texto" si no es viable a tiempo.
- **Sin autenticación** en el demo público.
- **Principios de código**: SOLID + KISS aplicados estructuralmente — el backend se organiza en capas (dominio puro / infraestructura / servicios / API), no en un solo módulo con todo mezclado.

## Datos de prueba (3 expedientes sintéticos)

1. **Limpio** — RFC oficial de sandbox del SAT `EKU9003173C9` ("Escuela Kemper Urgate SA de CV", documentado oficialmente para pruebas de timbrado CFDI), documentos con texto seleccionable, consistentes y vigentes → debe dar `safe`.
2. **Discrepancias mitigables** — comprobante de domicilio vencido + razón social distinta entre formulario y CSF (replica el ejemplo textual del propio PDF del challenge) → debe dar `review_required`.
3. **Bloqueo crítico** — RFC real tomado del listado 69-B "Definitivos" vigente del SAT (dato público real) → debe dar `high_risk`.

## Qué debe ingresar el usuario para iniciar el proceso

- **Mínimo para crear un expediente** (formulario de alta): razón social, RFC, domicilio fiscal declarado, nombre del representante legal.
- **Documentos, cada uno subible de forma independiente y opcional**: acta constitutiva, identificación del representante legal, poder notarial, **encargo conferido** (autorización electrónica del importador al agente aduanal vía VUCEM — distinto del poder notarial, ver sección "Alineación con el KYB real de Camtom"), comprobante de domicilio, RFC (documento), CSF, manifestación bajo protesta, datos de socios/beneficiario controlador cuando exista evidencia. Ningún documento es obligatorio para crear el expediente — los faltantes se penalizan vía el factor `doc_missing`, no bloquean el alta.
- **Dos caminos para registrar un documento, no solo uno** (el brief dice literalmente "cargar documentos **o** registrar metadata auditable" — esto se había leído de menos): (a) subir el archivo → pasa por extracción IA → revisión humana; (b) **sin archivo**, capturar manualmente los campos de ese `doc_type` directo en el formulario de revisión (`storage_path` nullable en `documentos`) → mismo estado final `human_reviewed`, mismo paso de scoring, salta los pasos 2-3 del pipeline. Ambos caminos quedan igual de auditables porque lo que se puntúa siempre es `fields` + `extraction_status`, no la existencia del archivo en sí.

## Alineación con el KYB real de Camtom

**Encargo conferido**: en el dominio aduanal mexicano, el poder notarial autoriza a una persona física a representar legalmente a la empresa en general (firmar contratos, actos jurídicos). El **encargo conferido** es distinto y más específico: es la autorización electrónica que el importador/exportador otorga a **ese agente aduanal en particular**, registrada vía VUCEM, y es la pieza documental que legalmente habilita al agente a despachar mercancía en nombre de ese cliente. Para una plataforma que construye literalmente el expediente de cumplimiento de un agente aduanal (Regla 1.4.14), este documento es al menos tan central como el poder notarial — es la prueba de la relación agente-cliente que se está evaluando. Se modela como un `doc_type` más (`encargo_conferido`), con su propio schema de extracción (RFC del agente, alcance/vigencia de la autorización) y su propio factor `doc_missing` si falta.

## Fuentes SAT verificadas (reales, accesibles hoy) — no hay archivos adjuntos por Camtom, solo URLs de gobierno

- Art. 69 (incumplidos): `wwwmat.sat.gob.mx/consultas/11981/...` (XLSX)
- Art. 69-B (EFOS, sub-estados Presunto/Desvirtuado/Definitivo/Sentencia Favorable): `wwwmat.sat.gob.mx/consultas/76674/...` (XLSX)
- Art. 69-B Bis: portal general `sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html` (CSV/XLS)
- **Art. 49 Bis: sin lista pública consultable hoy** — procedimiento administrativo interno del SAT, no un dataset publicado. El sistema lo documenta explícitamente (factor `art_49bis_no_verificable`, 0 puntos, marca `manual_review_required=true`) en vez de inventar una fuente.

**El ETL descarga estos archivos UNA VEZ por corrida y los carga a la tabla local `sat_lista_registros`. Toda consulta en tiempo de evaluación es un `SELECT` contra esa tabla — nunca se vuelve a tocar el sitio del SAT al evaluar un cliente.**

## Capa de Harness (IA tratada como componente no confiable)

Principio: el LLM puede alucinar y no es idempotente (mismo input, distinta salida entre llamadas). El sistema lo asume y lo encapsula, en vez de confiar en él:

1. **Idempotencia por hash**: cada llamada a IA (extracción de un documento, comparación de similitud de un par razón-social/domicilio) se cachea por hash del input exacto + versión de schema/prompt en una tabla `ai_call_cache`. Si ya existe un resultado para ese hash, se reutiliza — nunca se vuelve a preguntar al modelo para el mismo input exacto. Esto acota el no-determinismo a "la primera vez que se ve ese input", y la corrida del sistema completo es reproducible a partir de ahí.
2. **Validación en cada frontera**: schema Pydantic (forma) + reglas de negocio (ej. RFC extraído debe matchear el regex de RFC mexicano; si no, se descarta y se marca para revisión humana, nunca se acepta silenciosamente).
3. **Reintentos acotados con idempotencia**: máximo 2 reintentos si el parseo falla; un reintento no debe duplicar filas en `documentos` ni double-contar factores de score.
4. **El dato humano-confirmado es la única fuente de verdad**: el motor de scoring solo lee `documentos.fields` con `extraction_status='human_reviewed'`. El output crudo del LLM (`extracted_raw`) se guarda solo para auditoría/debug, nunca se usa directo para decidir.
5. **El LLM nunca decide la clasificación**: para razón social, domicilio y representante legal, el LLM solo devuelve `{similarity: 0-1, same_entity: bool}`; el motor de reglas en Python puro aplica un umbral fijo (distinto por campo, ver tabla de conciliación) para decidir si es discrepancia. RFC y fechas se comparan 100% determinísticamente sin LLM.
6. **Auditoría completa**: prompt, respuesta cruda, output parseado y cantidad de reintentos de cada llamada quedan guardados — es la base del "explicable" que exige el brief.
7. **Validación estructural de RFC, 100% determinística, sin LLM**: antes de cualquier consulta a `sat_lista_registros`, el RFC (declarado en el formulario o extraído de un documento) pasa por `domain/rfc.py::validar_estructura(rfc)` — regex de 12 caracteres para persona moral, fecha embebida (AAMMDD) calendario-válida, dígito verificador. Si falla, se dispara `rfc_formato_invalido` y NO se ejecuta la consulta SAT con ese RFC (evita el falso-positivo de "sin coincidencias" sobre un RFC que en realidad está mal escrito). Esto faltaba en versiones anteriores del plan — un RFC malformado tratado como "limpio" es el peor tipo de falla silenciosa para un sistema de compliance.

## Modelo de datos (Postgres/Supabase)

Tablas: `expedientes`, `documentos` (`storage_path` **nullable** — soporta el camino sin archivo, ver sección de intake; `extracted_raw` jsonb crudo + `fields` jsonb final post-revisión humana + `fecha_emision`/`fecha_vencimiento` desnormalizadas), `socios`, `sat_lista_registros` (tabla local indexada por RFC — lookup en milisegundos, alimentada por ETL), `sat_import_runs` (metadata de cada corrida ETL, da la antigüedad de la última revisión), `consultas_sat` (audit log: fuente, fecha/hora, RFC, resultado, referencia al `import_run_id` exacto), `factores_score` (cada factor con peso + explicación + evidencia), `evaluations` (snapshot de cada corrida del motor), `audit_log` (eventos generales), `ai_call_cache` (idempotencia de llamadas a IA, ver sección Harness).

## Motor de riesgo — rúbrica concreta

Ancla en los dos ejemplos del PDF (+20 comprobante vencido, +30 discrepancia razón social):

| factor_code | Condición | Puntos | Bloqueo crítico |
|---|---|---|---|
| `rfc_formato_invalido` | RFC (declarado o extraído) no pasa validación estructural (regex de 12 caracteres para persona moral + dígito verificador + fecha calendario válida) | 60 | **SÍ → fuerza mínimo `review_required`** (un RFC mal formado invalida cualquier resultado "limpio" de SAT — no hay forma de confiar en un "sin coincidencias" si el RFC consultado está mal) |
| `sat_69b_definitivo` | RFC en 69-B Definitivos | 100 | **SÍ → high_risk forzado** |
| `art_49bis_no_verificable` | Siempre presente (sin lista pública) | 0 | NO, marca revisión manual |
| `sat_69b_presunto` | RFC en 69-B Presunto | 40 | NO |
| `sat_69b_bis` | RFC en 69-B Bis | 35 | NO |
| `sat_69_incumplido` | RFC en Art. 69, **excepto cuando la única fracción que motiva la publicación es la VI** ("que se les hubiere condonado algún crédito fiscal" — verificado contra el texto legal real, no es incumplimiento, es una deuda que el propio SAT ya perdonó) | 25 (0 si fracción VI es la única razón) | NO |
| `disc_rfc` | RFC distinto entre documentos | 50 | NO |
| `disc_razon_social` | Discrepancia razón social | 30 | NO |
| `disc_representante` | Discrepancia rep. legal | 25 | NO |
| `csf_stale` | CSF fuera del mes vigente | 25 | NO |
| `doc_expired` | Comprobante de domicilio vencido | 20 | NO |
| `doc_expired_other` | Otro doc vencido | 20 c/u | NO |
| `disc_domicilio` | Discrepancia de domicilio | 20 | NO |
| `sat_lists_stale` | Última revisión SAT > 3 meses | 20 | NO |
| `socios_incompletos` | El acta constitutiva (u otro documento subido) **sí** trae evidencia de socios/accionistas/beneficiario controlador, pero la lista en `socios` quedó vacía o incompleta tras la revisión humana — el brief condiciona esto a "cuando exista evidencia documental", así que si la evidencia no existe (ej. acta no subida) esto NO se dispara, ya lo cubre `doc_missing` | 20 | NO |
| `doc_missing` | Documento obligatorio faltante (no se subió ningún archivo de ese tipo) | 15 c/u | NO |
| `doc_data_incomplete` | Documento SÍ subido, pero tras extracción + revisión humana algún campo obligatorio de ese tipo de documento quedó vacío (ej. CSF subida pero sin domicilio fiscal legible) — distinto de `doc_missing`, el archivo existe pero no aporta el dato | 15 c/u | NO |
| `manifestacion_incompleta` | La Manifestación bajo Protesta no contiene (o la revisión humana no confirmó) la cláusula de no encontrarse en los supuestos de los artículos 69-B y 49 Bis CFF | 20 | NO |
| `rep_legal_incompleto` | Datos del rep. legal incompletos | 15 | NO |
| `disc_fechas` | Inconsistencia de fechas | 15 | NO |

**Umbrales**: `critical_blocks` no vacío → `high_risk`. Si no: score ≥70 → `high_risk`; 30-69 → `review_required`; <30 → `safe`. Verificado contra los 3 casos de demo (0→safe, 50→review_required, 100/crítico→high_risk). El factor `rfc_formato_invalido` es la única excepción que fuerza un piso de `review_required` sin pasar por el bloqueo crítico clásico — está documentado así porque un RFC mal formado no es "riesgo alto confirmado", es "no podemos confiar en lo que ya evaluamos", que es semánticamente distinto.

`needs_update` es un estado de ciclo de vida independiente del score (doc vencido, CSF fuera de mes, listas >3 meses, o flag de cambio reportado por cliente).

El motor (`domain/scoring/`) es Python puro — funciones-factor independientes (Single Responsibility), agregación que no conoce el detalle de cada factor (Open/Closed: agregar un factor nuevo no toca el agregador), sin red ni LLM. 100% testeable con `pytest` y fixtures.

## Pipeline de extracción + conciliación

1. Alta de expediente (formulario: razón social, RFC, domicilio, rep. legal) → backend.
2. Upload de PDF → signed URL de Supabase Storage (emitida por el backend) → backend registra `documentos` con `extraction_status='pending'`.
3. `POST /documentos/{id}/extract`: extrae texto nativo del PDF; si no hay capa de texto usable, fallback a OCR (`pytesseract`, spike de fase 1) → LangChain (Python) + `ChatGroq` con structured output (schema Pydantic por `doc_type`), `temperature=0` → pasa por la capa de Harness (cache por hash, validación, reintentos) → guarda `extracted_raw` + `fields`, status `extracted`.
4. UI de **revisión humana obligatoria**: el usuario corrige los campos extraídos → `PATCH /documentos/{id}` → `status='human_reviewed'`. Solo estos entran al scoring. Si algún campo obligatorio de ese `doc_type` queda vacío incluso después de la revisión humana → dispara `doc_data_incomplete`, no se asume silenciosamente.
5. `POST /expedientes/{id}/evaluate`: conciliación → consultas SAT (lookup local, solo si el RFC pasó `validar_estructura`) → motor de reglas → `factores_score` + `evaluations`, incluyendo la `acción_sugerida` (ver abajo).

### Tabla de conciliación — qué se compara contra qué (esto se había perdido al reescribir a dos servicios, lo restauro explícito)

| Campo | Fuentes comparadas (todas contra todas, no solo pares) | Algoritmo | Umbral |
|---|---|---|---|
| RFC | formulario, CSF, acta, documento RFC | Determinístico (`normalize_rfc` + igualdad exacta) | Cualquier diferencia → `disc_rfc` |
| Razón social | formulario, CSF, acta | Semántico vía LLM (`{similarity, same_entity}`) | `similarity < 0.85` → `disc_razon_social` |
| Domicilio | formulario, CSF, comprobante de domicilio | Semántico vía LLM | `similarity < 0.75` (domicilios varían más en formato que razones sociales — abreviaturas de calle, "Col." vs "Colonia", números interiores — umbral más permisivo a propósito) → `disc_domicilio` |
| Representante legal (nombre) | formulario, poder notarial, identificación oficial | Semántico vía LLM, **mismo patrón que razón social** (decisión que faltaba explicitar: los nombres de personas también tienen variación legítima — segundo apellido omitido, acentos, orden) | `similarity < 0.90` (más estricto que domicilio: un nombre de persona debería casi-coincidir siempre, salvo error de captura) → `disc_representante` |
| Fechas (emisión/vigencia/vencimiento) | cada documento contra su propia regla de vigencia (ver tabla de vigencias) — esto NO es conciliación entre documentos, es validación de cada documento contra el reloj | Determinístico, comparación de fechas en Python | Según la tabla de vigencias |

### Tabla de vigencias por tipo de documento (no estaba explícita — "documentos vencidos" no puede ser una regla única para todos)

| `doc_type` | Regla de vigencia | Factor si vence |
|---|---|---|
| `comprobante_domicilio` | Fecha de emisión ≤ 3 meses de antigüedad respecto a hoy | `doc_expired` (+20) |
| `csf` | El campo de fecha de emisión de la CSF debe caer en el mes calendario actual (año+mes exactos) | `csf_stale` (+25), distinto de `doc_expired` |
| `identificacion_rep_legal` | Si el documento trae su propia fecha de vencimiento impresa (INE, pasaporte), se valida contra hoy; si no la trae, no se evalúa vigencia automática | `doc_expired_other` (+20) si vencida y la fecha es legible |
| `poder_notarial` | Sin vencimiento automático salvo revocación explícita declarada por el cliente — no se penaliza por antigüedad | N/A |
| `acta_constitutiva`, `rfc`, `manifestacion_protesta` | Sin vencimiento por antigüedad (son documentos fundacionales/declarativos, no periódicos) | N/A |

### Mecanismo de "cliente reporta cambios" (faltaba — el brief lo nombra como trigger de `needs_update` pero no había ningún endpoint ni botón que lo disparara)

`POST /expedientes/{id}/report-change` (body: `{reason: string}`) → marca `needs_update=true` + `needs_update_reason` + fila en `audit_log`. En la UI, un botón "Reportar cambio" en el detalle del expediente, visible siempre (no solo en casos `safe`), porque cualquier estado puede necesitar actualizarse.

### Acción sugerida (el brief la exige explícitamente en el ejemplo trabajado, no estaba modelada)

Mapeo determinístico (diccionario Python, no generado por LLM — coherente con la filosofía de harness) de `factor_code` → texto de remediación, ej. `doc_expired: "Actualizar comprobante de domicilio"`, `disc_razon_social: "Corregir razón social para que coincida entre documentos"`. `POST /expedientes/{id}/evaluate` concatena las acciones de todos los factores disparados (ordenadas por puntos, mayor primero) en `evaluations.summary.acciones_sugeridas: string[]`.

## ETL de listas del SAT

Parsers XLSX/CSV (Python: `pandas`/`openpyxl`), normalización de RFC (`normalize_rfc`: mayúsculas, sin espacios/guiones), upsert transaccional en `sat_lista_registros` con `import_batch_id` (borrar+insertar por `list_type` dentro de una transacción para reflejar bajas), registro en `sat_import_runs` (hash de archivo para detectar cambios). **El parser del Art. 69 debe capturar también la columna de fracción/supuesto de cada registro** (no solo RFC + situación) — sin esto es imposible aplicar la excepción de fracción VI que exige el propio PDF del challenge; se guarda en `sat_lista_registros.situacion` (texto crudo) y se parsea a un campo estructurado para que `sat_69_incumplido` pueda filtrar por fracción. Refresco vía endpoint admin manual (`POST /admin/sat/ingest`) como camino garantizado, con fallback de upload manual de archivo si la URL del SAT cambia o queda detrás de una página intermedia durante el fin de semana. Cron diario opcional vía Vercel Cron si el tiempo lo permite.

**Dos tipos de "antigüedad" distintos, no confundir**: (a) antigüedad del **dataset** (`sat_import_runs.started_at` — cuándo se corrió el ETL por última vez, afecta a TODOS los expedientes); (b) antigüedad de la **consulta de un expediente puntual** (`consultas_sat.consulted_at` — cuándo se evaluó ESTE cliente contra las listas, es el que dispara `sat_lists_stale`/`needs_update` a los 3 meses según el brief). Si el dataset (a) está muy desactualizado, ningún expediente individual lo refleja en su propio `needs_update` — es un riesgo operativo del sistema completo, no de un cliente puntual, así que se muestra como advertencia en `/admin`, no como factor de score de un expediente.

## Alineación con el KYB real de Camtom (investigación de su sitio público)

Investigué `camtomx.com/productos/kyb`, dos artículos de su academy, `/productos/docs` y su glosario, para hablar el mismo idioma que el producto real del CTO que evalúa esto — no para copiar su alcance (usan VUCEM, proveedores de datos privados, ISO 27001/SOC 2, que están fuera de alcance a propósito en una prueba de 48h con datos públicos).

**Cambios concretos y baratos que sí incorporamos:**
- **Nomenclatura del ciclo de vida**: Camtom describe 4 fases públicamente — Alta → Verificación → Monitoreo → Renovación. Las etiquetas de `expediente_status` en la UI usan estos mismos nombres (la lógica interna sigue siendo `draft/in_review/completed/needs_update`, solo cambia el copy visible).
- **`encargo_conferido` como `doc_type` separado de `poder_notarial`**: según el glosario de Camtom, el encargo conferido es la autorización electrónica (vía VUCEM) que el importador da al agente aduanal para representarlo — legalmente distinto del poder notarial del representante legal de la empresa. El PDF del challenge dice "poder o evidencia de representación, cuando aplique", lo cual cubre ambos conceptualmente, pero nombrar el encargo conferido explícitamente muestra investigación de dominio real, no solo lectura del brief. Verificación automática contra VUCEM queda fuera de alcance (documentado, mismo patrón que el Art. 49 Bis) — se captura como dato declarado/evidencia subida, no verificado en vivo.
- **Columna de completitud en el dashboard**: Camtom muestra "Cliente | Estatus | Expediente % | Acción" — agregamos el % de completitud (documentos presentes / documentos esperados) como columna visible, ya teníamos el dato, faltaba mostrarlo así.

**Validado, no cambiado:** su página de compliance monitoring dice que revalidan documentación "cada 90 días" — coincide exactamente con el umbral de 3 meses que ya usábamos por el brief. No es casualidad, es la misma cadencia que usa su propio producto en producción — vale la pena decirlo así en el README.

**Discrepancia documentada a propósito, no resuelta silenciosamente**: su producto real valida la CSF como vigente hasta "máximo 3 meses"; el brief de la prueba dice explícitamente "CSF fuera del mes vigente" (mes calendario exacto, más estricto). Implementamos la regla del brief porque es lo que se evalúa, pero lo documentamos en el README como una diferencia consciente, no un error — muestra que sabemos seguir un spec exacto aunque conozcamos la regla "real".

**A propósito, no implementado, y por qué**: integración con VUCEM, "Opinión de cumplimiento" del SAT (no hay vía pública anónima para verificarla, requiere credenciales del propio contribuyente), proveedores de datos privados. El README debe nombrar esto explícitamente como decisión de alcance informada, no como omisión.

## Sistema de diseño (frontend)

El frontend implementa el sistema de diseño definido en `frontend/DESIGN-clickhouse.md` (el archivo existe hoy en la raíz del repo y la Fase 1 lo mueve a `frontend/` justo después del scaffolding, para mantener la raíz limpia — ver Fase 1): canvas casi negro puro (`#0a0a0a`), amarillo eléctrico como único color de marca (`#faff69`) reservado para CTAs primarios, números de stat-callout y bandas full-bleed, tipografía Inter (700 para display, 600 para subtítulos/botones, 400 para body) y JetBrains Mono para bloques de código/datos tabulares. Border radius jerárquico (`8px` botones/inputs, `12px` cards). Sin sombras — la profundidad viene del contraste entre canvas y `surface-card` (`#1a1a1a`).

Mapeo específico a las pantallas del KYB (los colores semánticos ya están definidos en el `.md`, no hay que inventarlos):
- **Semáforo de decisión**: `safe` → `accent-emerald` (#22c55e), `review_required` → `warning` (#f59e0b), `high_risk` → `accent-rose` (#ef4444). Implementado como `badge-yellow`-style pill pero con estos colores semánticos en vez de amarillo (el amarillo de marca se reserva para CTAs, no para estados de negocio).
- **Stat-callouts** (`{typography.stat-display}`, 56px/700, siempre en amarillo): para métricas del dashboard ("Expedientes activos", "Promedio de score", "Pendientes de revisión").
- **`code-window-card`** (JetBrains Mono dentro de `surface-card`): para mostrar el JSON crudo de extracción (`extracted_raw`) en la vista de auditoría/debug — coherente con el uso que le da ClickHouse a este componente para mostrar artefactos técnicos.
- **`feature-card-dark`** / **`pricing-tier-card`-style**: para las cards de expediente individual y de cada documento.
- Tailwind se configura con estos tokens como theme extend (colores, radii, font-family) en `frontend/tailwind.config.ts` — no se inventan valores nuevos, se copian literal del `.md`.

## Componentes shadcn/ui a usar

**Corrección sobre mi verificación anterior**: dije que `attachment` y `shimmer` no existen en shadcn. Estaba mal, y la causa es interesante: shadcn ahora soporta **dos librerías de primitivos intercambiables — Radix (la clásica) y Base UI (la nueva, "estilo Rhea")** — elegible con la flag `-b, --base <radix|base>` en `shadcn create`/`shadcn init`. El MCP que usé resolvía por default contra el registro de Radix (`new-york-v4`), y *Attachment*, *Shimmer*, *Marker*, *Message*, *Message Scroller* y *Bubble* son componentes nuevos que **solo existen bajo el estilo `base`** (Base UI) — por eso mi búsqueda contra el registro por defecto no los encontraba. Confirmé esto con la página oficial del cambio (`docs/changelog/2026-01-base-ui`) y reproduciendo el error 404 contra la ruta de Radix antes de encontrar la ruta correcta.

**Decisión**: usamos el estilo **`base`** (Base UI), no Radix, como pediste. Esto se fija una sola vez al inicializar:

```bash
pnpm dlx shadcn@latest create -b base -t next
```

(o `init -b base` si el proyecto Next.js ya existe vía `create-next-app`). Una vez configurado en `components.json`, todos los `pnpm dlx shadcn@latest add <componente>` posteriores resuelven automáticamente contra el registro `base`, sin tener que repetir la flag.

De los componentes nuevos exclusivos de `base`, estos sí aplican a nuestro caso de uso (KYB, no chat) y los sumo al plan:
- **`Attachment` + `AttachmentGroup`** (estados `idle/uploading/processing/error/done`, acciones de remover/reintentar): reemplaza mi propuesta anterior de usar `item` genérico para la lista de documentos subidos — esto es literalmente lo que necesitamos (archivo + metadata + estado de subida/extracción + acción), ya viene con el estado que mapea 1:1 a nuestro `extraction_status`.
- **`Shimmer`** (utilidad CSS de texto, ej. "Extrayendo datos…"): para los textos de estado mientras corre la extracción de IA, la consulta al SAT o la evaluación — comunica "esto está procesando" sin un spinner genérico.
- **`Marker`** (compone con `Shimmer` + `Spinner`, patrón "Thinking… / Reading 4 files…" del propio ejemplo oficial): uso directo para visualizar los pasos del pipeline de harness en tiempo real — "Extrayendo texto del PDF…" → "Validando contra esquema…" → "Consultando listas del SAT…" → "Calculando score…", cada paso con shimmer mientras corre y check al completar. Esto convierte una decisión de arquitectura interna (la capa de harness, con sus pasos discretos y auditables) en una característica visible del producto — es la clase de detalle que diferencia esto de una prueba técnica promedio.

Los que **no** uso, a propósito: `Bubble`, `Message`, `Message Scroller` — son para UI de chat/conversación, y este dashboard no es un chat. Usarlos solo porque son nuevos sería forzar el componente al problema equivocado.

Instalación base: `pnpm dlx shadcn@latest add dashboard-01 item field command resizable chart input-group kbd attachment shimmer marker` + el resto de primitives listados abajo. Nunca se escriben estos componentes a mano.

| Pantalla | Componentes (primitives + blocks) | Por qué eleva la experiencia |
|---|---|---|
| Dashboard (lista de expedientes) | Block **`dashboard-01`** (sidebar + charts + data-table ya integrados) como base de layout, `badge`, `input`, `select`, `empty`, `skeleton` | Ahorra tiempo real (viene armado) y da una base visualmente profesional desde el primer commit de UI |
| Navegación | `sidebar` (variante `sidebar-07`, colapsa a iconos), `breadcrumb`, **`command`** + **`kbd`** (paleta de comandos Cmd+K para saltar a cualquier expediente por RFC/razón social) | El command palette es el tipo de detalle que un evaluador no espera en una prueba de 48h — alto impacto, bajo costo porque el componente viene completo |
| Alta de expediente | `field`, `field-group`, `input`, `input-group` (con `input-group-spinner` para validar RFC en vivo contra el formato), `select`, `button` | `input-group` con spinner inline comunica "esto está validando de verdad", no es cosmético |
| Subida de documentos | `field-choice-card` (elegir tipo de documento como tarjetas, no un dropdown ciego), **`Attachment`** (estado `idle`→`uploading`→`processing`→`done`/`error` mapeado 1:1 a `extraction_status`, con `Shimmer` en el título mientras `uploading`/`processing`), `progress`, `empty` | Tarjetas de elección reducen error de usuario al subir el documento equivocado; `Attachment` muestra de forma nativa exactamente el ciclo de vida de cada documento sin construirlo a mano |
| **Pipeline de extracción/evaluación en vivo** (visualiza la capa de Harness) | **`Marker`** + `Shimmer` + `Spinner`, una fila por paso ("Extrayendo texto…", "Validando esquema…", "Consultando SAT…", "Calculando score…"), check al completar cada uno | Convierte la arquitectura de harness (pasos discretos, auditables, con caché de idempotencia) en algo que el usuario VE corriendo, no solo en algo que existe en el backend |
| **Revisión humana de extracción** (la pantalla más crítica del harness) | **`resizable`** (panel izquierdo: preview del PDF: panel derecho: campos editables) con `field`/`input`/`textarea`, `alert` (campos de baja confianza marcados), `button-group` (confirmar/descartar) | Panel dividido y ajustable replica el patrón real de herramientas KYB comerciales (Ballerine, Sumsub) — el documento fuente y el dato extraído se ven a la vez, no en pestañas separadas |
| Detalle de expediente | `card`, `tabs`, **`item`** + `item-group`/`item-icon`/`item-avatar`/`item-link` (socios/beneficiario controlador), **`AttachmentGroup`** (documentos del expediente) | `item` da filas ricas para socios; `Attachment` reemplaza la idea anterior de usar `item` genérico para documentos, es el componente hecho para ese caso exacto |
| **Reporte de score explicable** | `card`, `badge` (semáforo con los colores de `DESIGN-clickhouse.md`), **`chart` → `chart-pie-donut-text`** (score total al centro, segmentos por categoría de factor) y/o `chart-bar-horizontal` (cada factor individual con sus puntos), `accordion` (detalle expandible), `tooltip` | Esto es directamente el requisito de "explicabilidad" del brief, visualizado en vez de solo listado — la diferencia entre "cumple el requisito" y "lo hace brillar" |
| Audit log / consultas SAT | `data-table`, `badge`, `separator`, `hover-card` (detalle del listado consultado al pasar el mouse) | |
| Admin SAT ETL | `card`, `button`, `progress`, `alert`, `spinner` | |
| Feedback async general | `sonner` (toasts de éxito/error en extracción, evaluación, ETL), `spinner`/`spinner-button` en cada acción que llama a Groq o a Supabase | Las llamadas a IA tardan segundos reales — sin feedback visual se siente roto, no lento |

**Nice-to-have si la fase 5 tiene margen** (no comprometido, se evalúa al llegar a esa fase): `carousel` para miniaturas de documentos, `context-menu` para acciones rápidas por fila en el dashboard.

Nota honesta sobre `Form`: el componente clásico `Form` (react-hook-form + zod) sí sigue existiendo en el registro real (`form` registry:ui), confirmado en la lista completa del MCP — mi duda anterior (basada en un WebFetch, no en el registro real) estaba mal planteada. Hay además variantes nuevas paralelas (`form-next-*`, `form-tanstack-*`, `form-formisch-*`) para otros manejadores de formularios — nos quedamos con el clásico `form` + react-hook-form, es el más documentado y el que mejor combina con `field` para los formularios largos (alta de expediente, revisión de extracción).

El MCP de shadcn que mencionaste sí está conectado ahora (`mcp__shadcn__*`) — se usó para verificar todo lo de esta sección en vivo, no se volvió a adivinar nada.

## Flujo de trabajo Git (Feature Branch Workflow)

- `main` protegida — nunca se commitea directo ahí.
- Una rama por fase del plan de implementación (`feat/scaffolding`, `feat/sat-etl`, `feat/scoring-engine`, `feat/ai-extraction`, `feat/dashboard-ui`, `feat/demo-data`), o más granular si una fase crece — seguir `work-unit-commits` para decidir el corte exacto de cada commit/PR dentro de una fase.
- Un PR por rama hacia `main`, usando las convenciones de la skill `branch-pr` (issue-first checks).
- Si una fase termina superando ~400 líneas de diff (umbral que ya usás en tu propio criterio de revisión), se parte en PRs encadenados siguiendo `chained-pr` en vez de mandar un PR gigante.
- Commits frecuentes dentro de cada rama, en español o inglés según convención del repo (a definir en el primer commit), mensajes en formato convencional.

## Estructura del monorepo

```
camtom-prueba-tecnica/
├─ frontend/                          # Next.js — proyecto Vercel #1
│  └─ src/
│     ├─ app/  (dashboard, alta, detalle, revisión, reporte, admin)
│     ├─ lib/api-client.ts            # cliente tipado del backend
│     ├─ components/ (ui/, ExpedienteCard, DocumentUploader, ExtractionReviewForm, ScoreReport)
│     └─ store/useExpedienteStore.ts
├─ backend/                           # FastAPI — proyecto Vercel #2
│  ├─ pyproject.toml / uv.lock        # uv
│  ├─ requirements.txt                # generado con `uv export` para el build de Vercel
│  ├─ vercel.json
│  └─ src/
│     ├─ main.py                      # instancia FastAPI (app), monta routers, CORS
│     ├─ api/routers/{expedientes,documentos,admin}.py   # capa delgada, sin lógica de negocio
│     ├─ api/deps.py                  # inyección de dependencias
│     ├─ domain/                      # lógica pura, sin IO/framework (SOLID: núcleo aislado)
│     │  ├─ scoring/{factors,engine,lifecycle}.py
│     │  ├─ reconciliation/reconcile.py
│     │  └─ rfc.py
│     ├─ infrastructure/              # adaptadores a sistemas externos
│     │  ├─ db/{models,repository}.py
│     │  ├─ storage/supabase_storage.py
│     │  ├─ sat/{sources,parsers,ingest,lookup}.py
│     │  └─ ai/{groq_client,schemas,extract,ocr,harness}.py
│     ├─ services/{expediente,extraction,evaluation}_service.py   # orquestación
│     └─ tests/  (pytest — engine, reconcile, harness)
└─ supabase/migrations/0001_init.sql
```

## Plan de implementación por fases

1. **Scaffolding + deploy de ambos servicios** (~1.5-2h) — todo con comandos oficiales, nada de boilerplate escrito a mano salvo donde no existe generador. **pnpm en todo el frontend, nada de npm/npx/yarn.**
   - `pnpm dlx create-next-app@latest frontend --typescript --tailwind --app` → `cd frontend && pnpm dlx shadcn@latest create -b base -t next` (o `init -b base` si `create` pide reconfigurar un proyecto ya existente — el estilo `base`/Base UI queda fijado en `components.json` desde este paso, no después) → `pnpm dlx shadcn@latest add <lista de la sección de componentes, incluyendo attachment shimmer marker>`.
   - `uv init backend` → `cd backend && uv add "fastapi[standard]" langchain langchain-groq pydantic sqlalchemy "supabase" pandas openpyxl pytest` (lista final de paquetes a confirmar en la fase, pero el comando es siempre `uv add`, nunca editar `pyproject.toml` a mano). **Gap real sin comando oficial**: no existe un generador de la estructura de carpetas en capas (`domain/`, `infrastructure/`, `services/`, `api/`) — eso sí se escribe a mano, `uv init` solo da el esqueleto de paquete Python.
   - `supabase init` → `supabase migration new init_schema` (genera el archivo vacío con timestamp correcto; el contenido SQL del schema sí se escribe a mano, no hay generador para un schema custom). **Online-only**: aplicar con `supabase link` + `supabase db push` al proyecto cloud (nunca `supabase start`); fallback = SQL Editor del dashboard.
   - `git init` (si no existe) → rama `main` → primer commit de scaffolding vacío en cada servicio → deploy de ambos a Vercel como proyectos separados (Root Directory `frontend/` y `backend/` respectivamente, build command del frontend usando pnpm) → confirmar que el frontend puede llamar a un endpoint de salud del backend (prueba end-to-end de la separación, con CORS ya configurado).
2. **Spike de OCR + ETL SAT + audit** (~4-5h): validar temprano si `pytesseract` funciona en el runtime de Vercel (definir el fallback si no); parsers de las 3 listas, normalización RFC, ingesta + fallback manual, lookup local. Verificable con un RFC real de 69-B Definitivos.
3. **Capa de Harness + motor de reglas** (~3-4h): cache de idempotencia, validación Pydantic + reglas de negocio, funciones-factor puras, umbrales, bloqueos críticos, `needs_update`. Tests con `pytest` cubriendo los 3 casos de demo + edge cases — esta fase es la más valorada por el brief.
4. **Extracción IA + conciliación** (~4-5h): extractor por `doc_type` con Pydantic + Groq, conciliación semántica con umbral fijo, integración con la capa de Harness.
5. **UI / dashboard** (~4-6h): lista de expedientes, alta, upload, pantalla de revisión humana (central), reporte de score explicable, audit log visible, badge `needs_update`.
6. **Datos de demo + pulido + README** (~2-3h): seed de los 3 expedientes, verificar las 3 clasificaciones esperadas, documentar decisiones de arquitectura (incluida la limitación del Art. 49 Bis y el resultado del spike de OCR), deploy final de ambos servicios.

Si el tiempo aprieta, la fase recortable es la 5 (UI funcional pero austera) — las fases 2-4 son innegociables.

## Riesgos documentados

- **`pytesseract` NO tiene el binario de Tesseract en Vercel serverless (Spike confirmado 2026-06-28).** Deploy de prueba con endpoint `POST /admin/ocr-spike` → `TesseractNotFoundError` en runtime. La librería Python se instala, pero falla al ejecutar porque el binario `tesseract` no existe en la imagen base de AWS Lambda de Vercel. **Reemplazo:** usar `PyMuPDF` (fitz) para extraer texto de PDFs con capa de texto directamente (sin OCR). Para PDFs escaneados (imagen), documentar como limitación conocida. Esto elimina la dependencia de `pytesseract` en Vercel y simplifica la Fase 4.
- Estabilidad del `similarity` del LLM entre llamadas → mitigado estructuralmente por la capa de Harness (cache por hash), no es un riesgo residual.
- Tamaño de archivos XLSX del SAT vs límites de las funciones serverless de Vercel → validar en fase 2; si excede, descargar a Storage primero y procesar aparte.
- Latencia/CORS entre dos servicios Vercel separados → configurar CORS explícito en FastAPI desde el primer deploy (fase 1), no al final.
- Catálogo de modelos de Groq cambia con frecuencia → centralizado en `infrastructure/ai/groq_client.py`.

## Verificación end-to-end

1. `pytest` en `backend/` — suite de scoring debe pasar con los 3 casos de demo (score 0/50/100+crítico → safe/review_required/high_risk).
2. Correr ETL contra las URLs reales del SAT y confirmar que `sat_lista_registros` se puebla con filas reales (no vacío, no mock).
3. Crear los 3 expedientes de demo en el dashboard desplegado, subir los PDFs sintéticos, confirmar que extracción + revisión humana + evaluación producen exactamente las 3 clasificaciones esperadas.
4. Revisar que `consultas_sat` registre fuente, fecha/hora, RFC y referencia al `import_run_id` para cada consulta.
5. Confirmar que ambos servicios (frontend y backend) están desplegados y accesibles públicamente sin login, y que el frontend efectivamente llama al backend (no a Supabase directo).

---

# Plan granular de implementación (formato `superpowers:writing-plans`)

> **Para agentes ejecutores:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para ejecutar tarea por tarea. Los pasos usan checkboxes (`- [ ]`) para tracking. Este bloque vive temporalmente dentro del archivo de plan de modo-plan por la restricción de solo-un-archivo; **la primera acción tras la aprobación es partirlo en `docs/superpowers/plans/<fecha>-<fase>.md` por fase**, más generar `CLAUDE.md` (ver cierre de este documento).

**Goal:** Construir y desplegar la plataforma KYB completa (backend FastAPI + frontend Next.js) descripta en las secciones anteriores de este documento, en 6 fases ejecutables independientemente.

**Architecture:** Dos servicios separados (`backend/` FastAPI-Python, `frontend/` Next.js-TS), comunicados por REST, con capas dominio/infraestructura/servicios/api en el backend, motor de reglas determinístico aislado de toda llamada a IA mediante una capa de Harness con caché de idempotencia.

**Tech Stack:** FastAPI, `uv`, LangChain (Python) + `langchain-groq`, Pydantic v2, `pandas`/`openpyxl`, `pytesseract`, Supabase (Postgres + Storage, vía cliente `supabase-py` — **no SQLAlchemy**, ver nota de simplificación abajo), pytest · Next.js (App Router), TypeScript, Tailwind, shadcn/ui (`-b base`), Zustand, pnpm.

## Global Constraints

- Todo dato que llega al motor de scoring pasa antes por `extraction_status='human_reviewed'` — nunca se puntúa un campo solo-IA sin confirmación humana.
- El LLM nunca produce la decisión final ni un valor que se compare con `==`; solo produce métricas (`similarity`, `same_entity`) interpretadas por umbrales fijos en Python.
- Toda llamada a IA pasa por la capa de Harness (`infrastructure/ai/harness.py`): hash de idempotencia, validación Pydantic, máx. 2 reintentos.
- Toda consulta a listas SAT es contra `sat_lista_registros` (tabla local) — nunca contra el sitio del SAT en tiempo de evaluación.
- `pnpm` en todo el frontend (nunca npm/yarn/npx). `uv` en todo el backend (nunca pip/poetry, nunca editar `pyproject.toml` a mano).
- **Python 3.13** en todo el backend — pineado vía `backend/.python-version` (`3.13`) y `requires-python = ">=3.13"` en `pyproject.toml`. Verificado: Vercel soporta 3.12/3.13/3.14, y 3.13 matchea el local instalado (3.13.3), eliminando version-skew local↔deploy. uv gestiona la versión; no instalar Python a mano.
- **Supabase solo online (cloud), nunca local**: no se corre `supabase start` ni el stack Docker local. Las migraciones se versionan en `supabase/migrations/` y se aplican al proyecto cloud con `supabase link` + `supabase db push` (verificado: `db push` conecta directo al remoto, no requiere Docker). Fallback sin CLI: pegar el SQL en el SQL Editor del dashboard.
- Nada de placeholders: cada paso de cada tarea tiene código real y completo, o el comando exacto a ejecutar.

**Nota de simplificación (KISS) respecto a la sección "Decisiones de arquitectura" más arriba**: esa sección listaba `sqlalchemy` como dependencia. La elimino acá: con `supabase-py` (el cliente oficial) alcanza para todo el acceso a datos de este proyecto — es una capa más fina sobre PostgREST, sin mapeo ORM que mantener, y el patrón repository (`infrastructure/db/repository.py`) lo envuelve igual sin que el resto del código note la diferencia. Mantener SQLAlchemy hubiese sido una capa de abstracción que el proyecto no necesita (YAGNI) — Supabase ya da el cliente tipado-suficiente. El comando de scaffolding de la Fase 1 queda `uv add "fastapi[standard]" langchain langchain-groq pydantic pandas openpyxl pytesseract supabase pytest httpx` (se suma `httpx` para los tests de los routers vía `TestClient`).

## Fase 1 — Scaffolding y deploy de ambos servicios

No es TDD (es setup de infraestructura) — son comandos verificables, no funciones a testear. Una sola "tarea" porque ningún paso individual es revisable por separado del resultado final (deploy verde).

**Archivos:**
- Crear: `frontend/` (vía CLI), `backend/` (vía CLI), `supabase/migrations/0001_init.sql`, `backend/vercel.json`, `frontend/vercel.json` (si Vercel lo requiere para el monorepo), `.gitignore` (raíz)

- [x] **Paso 1: Inicializar git y el monorepo**
```bash
git init
git branch -M main
mkdir -p frontend backend
```

- [x] **Paso 2: Scaffolding del frontend**
```bash
pnpm dlx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir=false --import-alias "@/*"
cd frontend
pnpm dlx shadcn@latest init -b base -t next -y
```
Verificar que `frontend/components.json` quedó con `"style"` apuntando al registro `base`, no `new-york`/`default` (Radix).

- [x] **Paso 2.1: Mover el spec de diseño dentro de `frontend/`** (root limpio — todo lo que no sea `CLAUDE.md`/`docs/`/configs de tooling vive en `frontend/` o `backend/`). Se hace ACÁ, después de `create-next-app`, porque ese comando se niega a correr si el directorio destino tiene archivos que no reconoce.
```bash
cd ..
mv DESIGN-clickhouse.md frontend/DESIGN-clickhouse.md
```
A partir de este punto el spec canónico es `frontend/DESIGN-clickhouse.md` — el `tailwind.config.ts` de la Fase 5 lo referencia desde ahí.

- [x] **Paso 2.2: `frontend/.env.example`** (no se pudo pre-crear antes: `create-next-app` aborta si el directorio destino tiene archivos fuera de su whitelist, y `.env.example` no está en ella — verificado contra la fuente del CLI). Se crea ACÁ, post-scaffold. Next.js usa `.env.local` para secretos locales; la única variable es la URL pública del backend (no es secreto, y recién se conoce tras el deploy del backend en el Paso 9).
```bash
# crear frontend/.env.example con este contenido exacto:
# (si un guard de permisos bloquea escribir archivos .env*, lo crea el usuario a mano — el contenido es trivial)
```
```
# Frontend (Next.js) — variables de entorno
# Copiá a `.env.local` y completá. `.env.local` está gitignoreado.
# URL pública del backend FastAPI desplegado en Vercel (se completa en el Paso 9).
NEXT_PUBLIC_API_URL=https://your-backend.vercel.app
```

- [x] **Paso 3: Scaffolding del backend**
```bash
cd ..
uv init backend --python 3.13
cd backend
uv add "fastapi[standard]" langchain langchain-groq pydantic pandas openpyxl pytesseract supabase pytest httpx
```
(`uv init --python 3.13` crea `backend/.python-version` con `3.13` y fija `requires-python` — la versión soportada por Vercel que matchea el local. `uv init` es no destructivo con archivos preexistentes y, como el `git init` raíz ya corrió en el Paso 1, no crea un `.git` anidado — verificado.)

- [x] **Paso 3.1: `backend/.env.example`** (crear con este contenido exacto; si un guard de permisos bloquea escribir archivos `.env*`, lo crea el usuario a mano). El usuario copia este archivo a `backend/.env` y completa los valores reales antes de las Fases 2-4. `uv init` (Paso 3) no lo pisa.
```
# Backend (FastAPI) — variables de entorno
# Copiá a `.env` y completá. `.env` está gitignoreado.
# En Vercel, las mismas variables van en Project Settings → Environment Variables.

# === Supabase (Postgres + Storage) ===
# Dashboard → Project Settings → API: https://supabase.com/dashboard
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# === Groq (LLM de extracción y conciliación, vía LangChain) ===
# https://console.groq.com/keys
GROQ_API_KEY=your-groq-api-key

# === CORS (opcional hasta Fase 5) ===
# URL pública del frontend en Vercel; en Fase 5 reemplaza el allow_origins=["*"].
# FRONTEND_URL=https://your-frontend.vercel.app
```

- [x] **Paso 4: Crear el FastAPI app mínimo (no hay generador oficial para esto, se escribe a mano)**

`backend/src/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Camtom KYB API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO en Fase 5: restringir al dominio real del frontend en Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [x] **Paso 5: Verificar localmente**
```bash
cd backend && uv run fastapi dev src/main.py
```
Esperado: `Serving at http://127.0.0.1:8000`, `GET /health` devuelve `{"status": "ok"}`, `GET /docs` muestra el Swagger UI.

- [x] **Paso 6: Generar requirements.txt para Vercel**
```bash
uv export --format requirements.txt --no-dev -o requirements.txt
```

- [x] **Paso 7: Estructura de carpetas en capas (sin generador, se crea a mano)**
```bash
mkdir -p src/api/routers src/domain/scoring src/domain/reconciliation src/infrastructure/db src/infrastructure/storage src/infrastructure/sat src/infrastructure/ai src/services src/tests
touch src/api/__init__.py src/api/routers/__init__.py src/domain/__init__.py src/domain/scoring/__init__.py src/domain/reconciliation/__init__.py src/infrastructure/__init__.py src/infrastructure/db/__init__.py src/infrastructure/storage/__init__.py src/infrastructure/sat/__init__.py src/infrastructure/ai/__init__.py src/services/__init__.py src/tests/__init__.py
```

- [x] **Paso 8: Migración inicial de Supabase (online-only, sin Docker/stack local)**
```bash
cd ..
supabase init                         # crea supabase/config.toml + supabase/migrations/ (no levanta nada)
supabase migration new init_schema    # genera el archivo vacío con timestamp correcto
```
Pegar el SQL completo de la sección "Modelo de datos" (todas las tablas: `expedientes`, `documentos`, `socios`, `sat_lista_registros`, `sat_import_runs`, `consultas_sat`, `factores_score`, `evaluations`, `audit_log`, `ai_call_cache`) en el archivo generado — el contenido SQL no tiene generador, se escribe a mano (ya está especificado completo más arriba en este documento).

Aplicar al proyecto **cloud** (NUNCA `supabase start` — no usamos stack local):
```bash
supabase login                        # o exportar SUPABASE_ACCESS_TOKEN
supabase link --project-ref <project-ref>   # ref del dashboard del proyecto online
supabase db push                      # aplica las migraciones al Postgres remoto (no requiere Docker — verificado)
```
Fallback sin CLI si `link`/`push` da fricción: pegar el mismo SQL en el **SQL Editor** del dashboard de Supabase. El archivo de migración queda igual versionado en el repo (reproducible), solo cambia el medio de aplicación.

- [x] **Paso 9: Deploy de ambos servicios a Vercel como proyectos separados** (con Root Directory corregido y Git integration conectada — ver Engram `camtom-kyb/vercel-git-integration-validation`)
- Proyecto 1: Root Directory `frontend/`, framework auto-detectado Next.js.
- Proyecto 2: Root Directory `backend/`, framework Python (Vercel detecta `app` de FastAPI automáticamente).
- Variables de entorno en el proyecto backend: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`.
- Variable en el proyecto frontend: `NEXT_PUBLIC_API_URL` (URL pública del backend recién desplegado).

- [x] **Paso 10: Verificación end-to-end de la separación**
Crear `frontend/src/lib/api-client.ts`:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
```
Llamarlo desde `frontend/src/app/page.tsx` (server component) y confirmar en el deploy de Vercel que el dato `{"status":"ok"}` llega desde el backend real, no hardcodeado.

- [x] **Paso 11: Commit y PR** (PRs #1, #2, #3, #4 mergeados a `main`)
```bash
git checkout -b feat/scaffolding
git add frontend backend supabase .gitignore
git commit -m "feat: scaffolding inicial de frontend (Next.js+shadcn base) y backend (FastAPI+uv)"
git push -u origin feat/scaffolding
```
PR hacia `main` siguiendo `branch-pr`.

## Fase 2 — Spike de OCR + ETL SAT + audit

### Task 2.1: RFC normalizer + validación de estructura

**Files:**
- Create: `backend/src/domain/rfc.py`
- Test: `backend/src/tests/test_rfc.py`

**Interfaces:**
- Produces: `normalize_rfc(raw: str) -> str`, `validar_estructura(rfc: str) -> bool` — usados por TODO el resto del backend (ETL, conciliación, scoring) para tratar el RFC siempre igual.

- [x] **Paso 1 — Test:**
```python
from domain.rfc import normalize_rfc, validar_estructura

def test_normalize_rfc_strips_and_uppercases():
    assert normalize_rfc(" eku900317-3c9 ") == "EKU9003173C9"

def test_validar_estructura_rfc_valido_sandbox_sat():
    assert validar_estructura("EKU9003173C9") is True

def test_validar_estructura_rechaza_fecha_imposible():
    assert validar_estructura("ABC991399XXX") is False

def test_validar_estructura_rechaza_longitud_incorrecta():
    assert validar_estructura("ABC123") is False
```
- [x] **Paso 2:** `uv run pytest src/tests/test_rfc.py -v` → falla (módulo no existe).
- [x] **Paso 3 — Implementación:** (ampliada con dígito verificador real módulo-11 — ver commit `0b76394` y Engram `camtom-prueba-tecnica`#38; el código verbatim de abajo es el original del plan, sin el dígito verificador)
```python
import re
from datetime import date

_RFC_MORAL_REGEX = re.compile(r"^[A-ZÑ&]{3}(\d{2})(\d{2})(\d{2})[A-Z0-9]{3}$")

def normalize_rfc(raw: str) -> str:
    return raw.strip().upper().replace(" ", "").replace("-", "")

def validar_estructura(rfc: str) -> bool:
    rfc = normalize_rfc(rfc)
    if len(rfc) != 12:
        return False
    match = _RFC_MORAL_REGEX.match(rfc)
    if not match:
        return False
    yy, mm, dd = (int(g) for g in match.groups())
    for century in (2000, 1900):
        try:
            date(century + yy, mm, dd)
            return True
        except ValueError:
            continue
    return False
```
- [x] **Paso 4:** `uv run pytest src/tests/test_rfc.py -v` → pasa (6 tests, incluye dígito verificador).
- [x] **Paso 5:** `git add src/domain/rfc.py src/tests/test_rfc.py && git commit -m "feat: normalizador y validador de estructura de RFC"`

### Task 2.2: Parser XLSX Art. 69 (con captura de fracción)

**Files:**
- Create: `backend/src/infrastructure/sat/sources.py`, `backend/src/infrastructure/sat/parsers.py`
- Test: `backend/src/tests/test_sat_parsers.py`

**Interfaces:**
- Consumes: `domain.rfc.normalize_rfc`
- Produces: `parse_art_69(xlsx_path: str) -> list[dict]` con claves `rfc`, `situacion`, `fraccion`; `es_unicamente_fraccion_vi(fraccion_raw: str) -> bool` — usado por el factor `sat_69_incumplido` en Fase 3 para aplicar la excepción que exige el brief.

- [x] **Paso 1 — Test (con fixture XLSX generado en memoria, no depende de internet):**
```python
import pandas as pd
import pytest
from infrastructure.sat.parsers import parse_art_69, es_unicamente_fraccion_vi

@pytest.fixture
def art_69_xlsx(tmp_path):
    df = pd.DataFrame({
        "RFC": ["abc010101xx1", "DEF020202XX2"],
        "Situación del contribuyente": ["No localizado", "Crédito fiscal firme"],
        "Fracción": ["I", "VI"],
    })
    path = tmp_path / "art69.xlsx"
    df.to_excel(path, index=False)
    return str(path)

def test_parse_art_69_normaliza_rfc(art_69_xlsx):
    rows = parse_art_69(art_69_xlsx)
    assert rows[0]["rfc"] == "ABC010101XX1"

def test_es_unicamente_fraccion_vi_true():
    assert es_unicamente_fraccion_vi("VI") is True

def test_es_unicamente_fraccion_vi_false_con_otra_fraccion():
    assert es_unicamente_fraccion_vi("I; VI") is False
```
- [x] **Paso 2:** `uv run pytest src/tests/test_sat_parsers.py -v` → falla.
- [x] **Paso 3 — Implementación:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SatSource:
    list_type: str
    url: str
    description: str

SAT_SOURCES: dict[str, SatSource] = {
    "art_69": SatSource("art_69", "https://wwwmat.sat.gob.mx/consultas/11981/consulta-la-relacion-de-contribuyentes-incumplidos", "Contribuyentes incumplidos (Art. 69 CFF)"),
    "art_69b": SatSource("art_69b", "https://wwwmat.sat.gob.mx/consultas/76674/consulta-la-relacion-de-contribuyentes-con-operaciones-presuntamente-inexistentes", "EFOS (Art. 69-B CFF)"),
    "art_69b_bis": SatSource("art_69b_bis", "https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html", "Pérdidas fiscales indebidas (Art. 69-B Bis CFF)"),
}
```
```python
import pandas as pd
from domain.rfc import normalize_rfc

# Encabezados a confirmar contra el archivo real descargado (paso de
# verificación de esta misma tarea) — el SAT no publica diccionario de
# datos estable. Único lugar del código que conoce el formato crudo.
ART_69_COLUMNS = {"rfc": "RFC", "situacion": "Situación del contribuyente", "fraccion": "Fracción"}

def parse_art_69(xlsx_path: str) -> list[dict]:
    df = pd.read_excel(xlsx_path)
    rows = []
    for _, row in df.iterrows():
        rfc = normalize_rfc(str(row[ART_69_COLUMNS["rfc"]]))
        if not rfc:
            continue
        rows.append({
            "rfc": rfc,
            "situacion": str(row[ART_69_COLUMNS["situacion"]]),
            "fraccion": str(row.get(ART_69_COLUMNS["fraccion"], "")).strip(),
        })
    return rows

def es_unicamente_fraccion_vi(fraccion_raw: str) -> bool:
    fracciones = {f.strip() for f in fraccion_raw.replace(",", ";").split(";") if f.strip()}
    return fracciones == {"VI"}
```
- [x] **Paso 4:** `uv run pytest src/tests/test_sat_parsers.py -v` → pasa.
- [x] **Paso 5:** BLOQUEADO externamente, documentado: la página del SAT (`art_69`) no expone un link estático de XLSX — el archivo se genera dinámicamente vía formulario (probado con `curl`/`WebFetch`, sin éxito). `ART_69_COLUMNS` queda con los valores asumidos del brief, sin confirmar. Ver Engram `discovery/sat-art-69-xlsx-no-tiene-url-de-descarga-estatica`.
- [x] **Paso 6:** `git commit -m "feat: parser XLSX Art. 69 con captura de fracción"`

### Task 2.3: Parser XLSX Art. 69-B (con sub-estados EFOS)

**Files:**
- Modify: `backend/src/infrastructure/sat/parsers.py`
- Modify: `backend/src/tests/test_sat_parsers.py`

**Interfaces:**
- Produces: `parse_art_69b(xlsx_path: str) -> list[dict]` con claves `rfc`, `razon_social`, `art69b_substate` (∈ `presunto/desvirtuado/definitivo/sentencia_favorable`), `situacion`.

- [x] **Paso 1 — Test:** implementado tal cual el brief (commit `f84b9da`).
- [x] **Paso 2:** falla (confirmado antes de implementar).
- [x] **Paso 3 — Implementación:** implementado tal cual el brief inicialmente (commit `f84b9da`), luego corregido en dos rondas tras revisión de contexto fresco (ver nota abajo) — commits `32dc12e` y `de21d04`.
- [x] **Paso 4:** pasa (18/18 tests del módulo SAT, suite completa del backend en verde).
- [x] **Paso 5:** **BLOQUEADO externamente** — mismo motivo que Task 2.2: el SAT no publica una URL estática de descarga para el Art. 69-B; el archivo se genera vía formulario dinámico, no es fetcheable directo con curl/WebFetch. `ART_69B_COLUMNS` queda sin verificar contra un archivo real (riesgo documentado, heredado a Task 2.5/2.7).
- [x] **Paso 6:** `git commit -m "feat: parser XLSX Art. 69-B con sub-estados EFOS"` (commit `f84b9da`).

> **Desvío del brief (post-revisión de contexto fresco):** el código verbatim del brief usaba `_ART_69B_SUBSTATE_MAP.get(situacion_raw)` sin default — un sub-estado no mapeado (acento, variante de capitalización fuera de alcance del `.lower()`, etc.) producía `art69b_substate=None` de forma silenciosa. Como este campo alimenta el bloqueo crítico `sat_69b_definitivo` (100 puntos, fuerza `high_risk`) en Fase 3, un `None` silencioso podía perder un bloqueo real sin ningún error visible (fail-open). Corregido a fail-closed: `raise ValueError` explícito ante cualquier situación no mapeada (commit `32dc12e`). Una revisión de contexto fresco posterior detectó que ese mismo `raise` rompía sobre filas vacías/de nota al pie del Excel (RFC/situación NaN) en lugar de descartarlas — corregido extendiendo el filtro de skip, más cobertura de test para las 4 variantes de sub-estado (commit `de21d04`). Decisión y verificación documentadas en Engram.

### Task 2.4: Ingesta transaccional a `sat_lista_registros`

**Files:**
- Create: `backend/src/infrastructure/sat/ingest.py`
- Create: `backend/src/tests/conftest.py` - Test: `backend/src/tests/test_sat_ingest.py`

**Interfaces:**
- Consumes: `parse_art_69`, `parse_art_69b`, `SAT_SOURCES`
- Produces: `ingest_list(supabase_client, list_type: str, xlsx_path: str) -> dict` con `{"run_id": str, "rows_imported": int}` — usado por el endpoint admin (Task 2.7).

- [x] **Paso 1 — `conftest.py`:** implementado y extendido (ver nota abajo) — commits `38dff63`, `caf44cf`, `dbb1f31`.
- [x] **Paso 2 — Test:** implementado tal cual el brief + 5 tests adicionales (ver nota).
- [x] **Paso 3:** falla (confirmado antes de implementar).
- [x] **Paso 4 — Implementación:** implementado tal cual el brief inicialmente, luego corregido tras revisión de contexto fresco (ver nota abajo).
```python
import hashlib, uuid
from datetime import datetime, timezone
from infrastructure.sat.parsers import parse_art_69, parse_art_69b
from infrastructure.sat.sources import SAT_SOURCES

def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def ingest_list(supabase_client, list_type: str, xlsx_path: str) -> dict:
    source = SAT_SOURCES[list_type]
    run_id = str(uuid.uuid4())
    supabase_client.table("sat_import_runs").insert({
        "id": run_id, "list_type": list_type, "source_url": source.url,
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
        "file_hash": file_hash(xlsx_path),
    }).execute()

    parser = {"art_69": parse_art_69, "art_69b": parse_art_69b}[list_type]
    rows = parser(xlsx_path)
    batch_id = str(uuid.uuid4())
    records = [{
        "list_type": list_type, "rfc": r["rfc"], "razon_social": r.get("razon_social"),
        "art69b_substate": r.get("art69b_substate"), "situacion": r.get("situacion"),
        "source_url": source.url, "import_batch_id": batch_id,
    } for r in rows]

    supabase_client.table("sat_lista_registros").delete().eq("list_type", list_type).execute()
    if records:
        supabase_client.table("sat_lista_registros").insert(records).execute()

    supabase_client.table("sat_import_runs").update({
        "status": "success", "rows_imported": len(records),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", run_id).execute()
    return {"run_id": run_id, "rows_imported": len(records)}
```
- [x] **Paso 5:** pasa (25/25 tests del suite completo del backend).
- [x] **Paso 6:** `git commit -m "feat: ingesta transaccional de listas SAT a tabla local"` (commit `38dff63`).

> **Desvíos del brief (post-implementación + 2 rondas de revisión de contexto fresco):**
> 1. El implementador cambió los `KeyError` opacos del brief (`SAT_SOURCES[list_type]` y el dict de parsers) por `ValueError` explícitos, validados ANTES de escribir nada en `sat_import_runs` — evita un run huérfano en `status="running"` si `list_type` está registrado en `SAT_SOURCES` pero no tiene parser (caso real: `art_69b_bis`). Aceptado por la review.
> 2. **CRITICAL real encontrado por la review fresca**: el código del brief hacía `delete` de los registros viejos ANTES del `insert` de los nuevos, sin ninguna garantía atómica real (4 llamadas HTTP independientes a Supabase) — pese a que el título de la tarea dice "ingesta transaccional". Si el insert fallaba a mitad de camino, la lista quedaba vacía (viejos borrados, nuevos no insertados) y el run quedaba en `status="running"` para siempre, sin error visible. Riesgo alto porque esta lista alimenta el bloqueo crítico `sat_69b_definitivo` (100 pts) en Fase 3. **Fix (commit `caf44cf`):** insertar primero los registros nuevos (con su propio `batch_id`), borrar los viejos filtrando por `import_batch_id != batch_id` solo si el insert tuvo éxito, y envolver todo en `try/except` que marca `status="failed"` y re-lanza ante cualquier excepción.
> 3. **WARNING de la segunda review (no bloqueante, corregido de todos modos)**: el fake de test (`_FakeQuery.neq`) usaba semántica Python (`!=`) en vez de la semántica NULL-aware real de SQL/PostgREST (`NULL <> X` nunca es `true`), lo cual podía ocultar filas huérfanas con `import_batch_id IS NULL` que nunca se borrarían en producción. Mitigado hoy por el `NOT NULL` del schema, pero corregido en el fake para que sea fiel a Postgres independientemente del esquema actual (commit `dbb1f31`).
> 4. Veredicto final de la review: **APPROVED**. Decisión y verificación documentadas en Engram y en `.superpowers/sdd/progress.md`.

### Task 2.5: Lookup local + audit log (`consultas_sat`)

**Files:**
- Create: `backend/src/infrastructure/sat/lookup.py`
- Test: `backend/src/tests/test_sat_lookup.py`

**Interfaces:**
- Consumes: `domain.rfc.validar_estructura`, `infrastructure.sat.parsers.es_unicamente_fraccion_vi`, `SAT_SOURCES`
- Produces: `consultar_rfc_en_listas(supabase_client, expediente_id: str, rfc: str) -> list[dict]` — cada item `{"list_type": str, "match_substate": str|None}` para los hits que SÍ deben generar factor de riesgo (ya filtrados por la excepción de fracción VI). Si el RFC es inválido devuelve `[{"factor_code": "rfc_formato_invalido", "rfc": rfc}]` sin tocar la red ni la tabla local. **Consumido directamente por Task 3.2 (factores de listas SAT).**

- [x] **Paso 1 — Test:**
```python
from infrastructure.sat.lookup import consultar_rfc_en_listas

def test_rfc_invalido_no_consulta_nada(fake_supabase):
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "ABC123")
    assert resultado == [{"factor_code": "rfc_formato_invalido", "rfc": "ABC123"}]
    assert "consultas_sat" not in fake_supabase.store

def test_rfc_limpio_no_genera_hits(fake_supabase):
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")
    assert resultado == []
    assert len(fake_supabase.store["consultas_sat"]) == 2  # art_69 + art_69b consultados y logueados

def test_rfc_en_69b_definitivo_genera_hit(fake_supabase):
    fake_supabase.store["sat_lista_registros"] = [
        {"list_type": "art_69b", "rfc": "GHI030303XX3", "art69b_substate": "definitivo", "situacion": "definitivo"}
    ]
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "GHI030303XX3")
    assert {"list_type": "art_69b", "match_substate": "definitivo"} in resultado

def test_import_run_id_queda_seteado_con_run_success_previo(fake_supabase):
    fake_supabase.store["sat_import_runs"] = [
        {"id": "run-1", "list_type": "art_69", "status": "success", "started_at": "2026-06-27T00:00:00Z"}
    ]
    fake_supabase.store["sat_lista_registros"] = [
        {"list_type": "art_69", "rfc": "EKU9003173C9", "situacion": "I"}
    ]
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")
    consulta = fake_supabase.store["consultas_sat"][0]
    assert consulta["import_run_id"] == "run-1"

def test_import_run_id_queda_none_si_no_hay_run_success(fake_supabase):
    fake_supabase.store["sat_import_runs"] = []
    fake_supabase.store["sat_lista_registros"] = [
        {"list_type": "art_69", "rfc": "EKU9003173C9", "situacion": "I"}
    ]
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")
    consulta = fake_supabase.store["consultas_sat"][0]
    assert consulta["import_run_id"] is None
```
- [x] **Paso 2:** falla (confirmado antes de implementar).
- [x] **Paso 3 — Implementación real:** (ver commit `f30511f` — diff con el plan original abajo)
  - Se agregó `_LISTAS_SIN_PARSER = {"art_69b_bis"}` en vez del `if list_type == "art_69b_bis": continue` suelto, para centralizar la exclusión en un solo lugar.
  - Se agregó `_resolver_run_id_mas_reciente()` para poblar `consultas_sat.import_run_id` (columna agregada en la migración, commit `462b750`), que da trazabilidad al run de ingesta que originó cada consulta.
  - Se filtró en Python (no vía `.order().limit()` de PostgREST) porque el `FakeSupabase` no implementa esos métodos fielmente y el test pasaría sin verificar nada real.
- [x] **Paso 4:** pasa (5 tests en `test_sat_lookup.py`, suite completa del backend en verde).
- [x] **Paso 5:** `git commit -m "feat: lookup local de RFC contra listas SAT con audit log"` (commit `f30511f`).

### Task 2.6: Spike de OCR (`pytesseract` en runtime serverless de Vercel)

No es TDD — es una investigación con un resultado binario documentado, no una función a testear todavía.

- [x] **Paso 1:** `uv add pdf2image pillow` — pytesseract ya estaba como dependencia transitiva.
- [x] **Paso 2:** Creado `backend/src/infrastructure/ai/ocr.py` con `ocr_imagen()` que llama a `pytesseract.image_to_string()`.
- [x] **Paso 3:** Deployado a Vercel con endpoint `POST /admin/ocr-spike`. Verificado: **Tesseract NO disponible** — `TesseractNotFoundError` en runtime serverless.
- [x] **Paso 4:** Documentado en la sección "Riesgos documentados" (ver abajo). Recomendación: usar PyMuPDF/pdfplumber para extraer texto de PDFs con capa de texto, que es el caso de uso de esta demo.
- [x] **Paso 5:** `git commit -m "spike: validar disponibilidad de Tesseract OCR en runtime Vercel"` — resultado: NO disponible, se documenta limitación.

### Task 2.7: Endpoint admin de ingesta SAT

**Files:**
- Create: `backend/src/api/routers/admin.py`
- Modify: `backend/src/main.py` (montar el router)
- Test: `backend/src/tests/test_admin_router.py`

**Interfaces:**
- Consumes: `infrastructure.sat.ingest.ingest_list`
- Produces: endpoint `POST /admin/sat/ingest/{list_type}` (multipart, recibe el XLSX subido a mano como fallback si la descarga directa desde el SAT falla).

    - [x] **Paso 1 — Test:** implementados 2 tests (art_69b y art_69) en `test_admin_router.py`.
    - [x] **Paso 2:** falla (confirmado antes de implementar).
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
    - [x] **Paso 5:** commit y push para PR.

## Fase 3 — Capa de Harness + motor de reglas (la fase más valorada por el brief)

### Task 3.1: Caché de idempotencia para llamadas a IA (`infrastructure/ai/harness.py`)

**Files:**
- Create: `backend/src/infrastructure/ai/harness.py`
- Test: `backend/src/tests/test_harness.py`

**Interfaces:**
- Produces: `compute_input_hash(call_type: str, payload: dict) -> str`, `call_with_harness(supabase_client, call_type: str, payload: dict, compute: Callable[[], dict], max_retries: int = 2) -> dict` — **toda** llamada real a Groq en Fase 4 pasa por esta función, nunca se llama al modelo directo.

- [ ] **Paso 1 — Test (sin red real, `compute` es una función inyectada):**
```python
import pytest
from infrastructure.ai.harness import call_with_harness, compute_input_hash

def test_compute_input_hash_es_estable_para_el_mismo_payload():
    assert compute_input_hash("extraction", {"a": 1, "b": 2}) == compute_input_hash("extraction", {"b": 2, "a": 1})

def test_call_with_harness_cachea_y_no_vuelve_a_llamar(fake_supabase):
    llamadas = []
    def compute():
        llamadas.append(1)
        return {"similarity": 0.9}
    r1 = call_with_harness(fake_supabase, "similarity", {"a": "x"}, compute)
    r2 = call_with_harness(fake_supabase, "similarity", {"a": "x"}, compute)
    assert r1 == r2 == {"similarity": 0.9}
    assert len(llamadas) == 1

def test_call_with_harness_agota_reintentos_y_lanza(fake_supabase):
    def compute_que_siempre_falla():
        raise ValueError("parseo inválido")
    with pytest.raises(RuntimeError):
        call_with_harness(fake_supabase, "extraction", {"doc": "x"}, compute_que_siempre_falla, max_retries=2)
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
import hashlib, json, uuid
from datetime import datetime, timezone
from typing import Callable

SCHEMA_VERSION = "v1"

def compute_input_hash(call_type: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{call_type}:{SCHEMA_VERSION}:{canonical}".encode("utf-8")).hexdigest()

def call_with_harness(supabase_client, call_type: str, payload: dict, compute: Callable[[], dict], max_retries: int = 2) -> dict:
    input_hash = compute_input_hash(call_type, payload)
    cached = supabase_client.table("ai_call_cache").select("*").eq("input_hash", input_hash).execute()
    if cached.data:
        return cached.data[0]["result"]

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = compute()
            supabase_client.table("ai_call_cache").insert({
                "id": str(uuid.uuid4()), "input_hash": input_hash, "call_type": call_type,
                "schema_version": SCHEMA_VERSION, "result": result, "retries": attempt,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return result
        except Exception as exc:  # noqa: BLE001 — frontera deliberada: cualquier falla cae al reintento
            last_error = exc
            continue
    raise RuntimeError(f"Harness: agotados los reintentos para {call_type}") from last_error
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: capa de harness con cache de idempotencia para llamadas IA"`

### Task 3.2: Factores de listas fiscales SAT

**Files:**
- Create: `backend/src/domain/scoring/factors.py`
- Test: `backend/src/tests/test_scoring_factors_sat.py`

**Interfaces:**
- Consumes: salida de `infrastructure.sat.lookup.consultar_rfc_en_listas` (Task 2.5)
- Produces: `Factor` (dataclass: `factor_code, points, is_critical_block, detail, evidence`), `factores_listas_sat(sat_hits: list[dict]) -> list[Factor]`

- [ ] **Paso 1 — Test:**
```python
from domain.scoring.factors import factores_listas_sat

def test_rfc_invalido_solo_genera_ese_factor():
    factores = factores_listas_sat([{"factor_code": "rfc_formato_invalido", "rfc": "ABC123"}])
    assert [f.factor_code for f in factores] == ["rfc_formato_invalido"]
    assert factores[0].points == 60

def test_sin_hits_solo_genera_art_49bis():
    factores = factores_listas_sat([])
    assert len(factores) == 1 and factores[0].factor_code == "art_49bis_no_verificable" and factores[0].points == 0

def test_69b_definitivo_es_bloqueo_critico():
    factores = factores_listas_sat([{"list_type": "art_69b", "match_substate": "definitivo"}])
    bloqueo = next(f for f in factores if f.factor_code == "sat_69b_definitivo")
    assert bloqueo.is_critical_block is True and bloqueo.points == 100
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Factor:
    factor_code: str
    points: int
    is_critical_block: bool
    detail: str
    evidence: dict | None = None

def factores_listas_sat(sat_hits: list[dict]) -> list[Factor]:
    if any(h.get("factor_code") == "rfc_formato_invalido" for h in sat_hits):
        return [Factor("rfc_formato_invalido", 60, False, "El RFC no pasa la validación de estructura — no se puede confiar en ninguna consulta SAT hecha con este dato.")]

    factores = []
    for hit in sat_hits:
        if hit["list_type"] == "art_69b" and hit["match_substate"] == "definitivo":
            factores.append(Factor("sat_69b_definitivo", 100, True, "RFC localizado en el listado definitivo de EFOS (Art. 69-B CFF)."))
        elif hit["list_type"] == "art_69b" and hit["match_substate"] == "presunto":
            factores.append(Factor("sat_69b_presunto", 40, False, "RFC localizado en el listado presunto de EFOS (Art. 69-B CFF)."))
        elif hit["list_type"] == "art_69b_bis":
            factores.append(Factor("sat_69b_bis", 35, False, "RFC en el listado de transmisión indebida de pérdidas fiscales (Art. 69-B Bis CFF)."))
        elif hit["list_type"] == "art_69":
            factores.append(Factor("sat_69_incumplido", 25, False, "RFC en el listado de contribuyentes incumplidos (Art. 69 CFF)."))

    factores.append(Factor("art_49bis_no_verificable", 0, False, "El Art. 49 Bis CFF no tiene lista pública consultable — requiere revisión manual.", evidence={"manual_review_required": True}))
    return factores
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: factores de score para listas fiscales SAT"`

### Task 3.3: Conciliación (umbrales fijos) + factores de discrepancia

**Files:**
- Create: `backend/src/domain/reconciliation/reconcile.py`
- Modify: `backend/src/domain/scoring/factors.py`
- Test: `backend/src/tests/test_reconcile.py`

**Interfaces:**
- Produces: `ResultadoConciliacion` (dataclass de 5 booleanos), `reconciliar(rfcs, similarity_razon_social, similarity_domicilio, similarity_representante, fechas_validas) -> ResultadoConciliacion`, `factores_discrepancias(resultado: ResultadoConciliacion) -> list[Factor]`. **`similarity_*` son dicts `{"similarity": float, "same_entity": bool}` que en Fase 4 vienen de `call_with_harness`; acá se testean con valores inyectados, sin LLM real — el umbral fijo es lo único que decide.**

- [ ] **Paso 1 — Test:**
```python
from domain.reconciliation.reconcile import reconciliar

def test_rfc_discrepante_cuando_hay_mas_de_un_valor_distinto():
    r = reconciliar(["ABC010101XX1", "ABC010101XX1", "DEF020202XX2"],
                     {"similarity": 1.0, "same_entity": True}, {"similarity": 1.0, "same_entity": True},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.rfc_discrepante is True

def test_razon_social_no_discrepante_si_similarity_supera_umbral():
    r = reconciliar(["X"], {"similarity": 0.92, "same_entity": False}, {"similarity": 1.0, "same_entity": True},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.razon_social_discrepante is False

def test_domicilio_discrepante_con_umbral_mas_permisivo():
    r = reconciliar(["X"], {"similarity": 1.0, "same_entity": True}, {"similarity": 0.70, "same_entity": False},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.domicilio_discrepante is True
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from dataclasses import dataclass

UMBRALES = {"razon_social": 0.85, "domicilio": 0.75, "representante_legal": 0.90}

@dataclass(frozen=True)
class ResultadoConciliacion:
    rfc_discrepante: bool
    razon_social_discrepante: bool
    domicilio_discrepante: bool
    representante_discrepante: bool
    fechas_inconsistentes: bool

def reconciliar(rfcs, similarity_razon_social, similarity_domicilio, similarity_representante, fechas_validas) -> ResultadoConciliacion:
    rfcs_norm = {r.strip().upper() for r in rfcs if r}
    return ResultadoConciliacion(
        rfc_discrepante=len(rfcs_norm) > 1,
        razon_social_discrepante=(not similarity_razon_social["same_entity"]) and similarity_razon_social["similarity"] < UMBRALES["razon_social"],
        domicilio_discrepante=(not similarity_domicilio["same_entity"]) and similarity_domicilio["similarity"] < UMBRALES["domicilio"],
        representante_discrepante=(not similarity_representante["same_entity"]) and similarity_representante["similarity"] < UMBRALES["representante_legal"],
        fechas_inconsistentes=not fechas_validas,
    )
```
Agregar a `factors.py`:
```python
def factores_discrepancias(resultado) -> list[Factor]:
    factores = []
    if resultado.rfc_discrepante:
        factores.append(Factor("disc_rfc", 50, False, "El RFC no coincide entre los documentos del expediente."))
    if resultado.razon_social_discrepante:
        factores.append(Factor("disc_razon_social", 30, False, "La razón social no coincide de forma material entre los documentos."))
    if resultado.domicilio_discrepante:
        factores.append(Factor("disc_domicilio", 20, False, "El domicilio no coincide de forma material entre los documentos."))
    if resultado.representante_discrepante:
        factores.append(Factor("disc_representante", 25, False, "El nombre del representante legal no coincide entre los documentos."))
    if resultado.fechas_inconsistentes:
        factores.append(Factor("disc_fechas", 15, False, "Inconsistencia entre fechas de emisión/vigencia/vencimiento."))
    return factores
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: conciliacion con umbrales fijos y factores de discrepancia"`

### Task 3.4: Factores de completitud y vigencia documental

**Files:**
- Modify: `backend/src/domain/scoring/factors.py`
- Test: `backend/src/tests/test_scoring_factors_completitud.py`

**Interfaces:**
- Produces: `factores_completitud(documentos: list[dict], socios: list[dict], hoy: date) -> list[Factor]`

- [ ] **Paso 1 — Test:**
```python
from datetime import date
from domain.scoring.factors import factores_completitud

def test_doc_missing_por_cada_tipo_ausente():
    factores = factores_completitud([], [], date(2026, 6, 28))
    assert [f.factor_code for f in factores].count("doc_missing") == 8

def test_comprobante_domicilio_vencido():
    documentos = [{"id": "1", "doc_type": "comprobante_domicilio", "extraction_status": "human_reviewed", "fields": {"domicilio": "x"}, "fecha_emision": date(2026, 1, 1)}]
    assert any(f.factor_code == "doc_expired" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_csf_fuera_de_mes_vigente():
    documentos = [{"id": "1", "doc_type": "csf", "extraction_status": "human_reviewed", "fields": {"rfc": "x"}, "fecha_emision": date(2026, 5, 1)}]
    assert any(f.factor_code == "csf_stale" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_acta_presente_sin_socios_dispara_socios_incompletos():
    documentos = [{"id": "1", "doc_type": "acta_constitutiva", "extraction_status": "human_reviewed", "fields": {"razon_social": "x"}, "fecha_emision": None}]
    assert any(f.factor_code == "socios_incompletos" for f in factores_completitud(documentos, [], date(2026, 6, 28)))
```
- [ ] **Paso 2:** falla.
- [ ] **Paso 3 — Implementación (agregar a `factors.py`):**
```python
DOCUMENTOS_ESPERADOS = {
    "acta_constitutiva", "identificacion_rep_legal", "poder_notarial", "encargo_conferido",
    "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
}
VIGENCIA_DIAS = {"comprobante_domicilio": 90}

def factores_completitud(documentos: list[dict], socios: list[dict], hoy) -> list[Factor]:
    factores = []
    presentes = {d["doc_type"] for d in documentos}
    for esperado in DOCUMENTOS_ESPERADOS - presentes:
        factores.append(Factor("doc_missing", 15, False, f"Falta el documento: {esperado}.", evidence={"doc_type": esperado}))

    for doc in documentos:
        if doc["extraction_status"] != "human_reviewed":
            continue
        fields = doc.get("fields") or {}
        if any(v in (None, "") for v in fields.values()):
            factores.append(Factor("doc_data_incomplete", 15, False, f"El documento {doc['doc_type']} no aportó todos los campos obligatorios.", evidence={"documento_id": doc["id"]}))
        if doc["doc_type"] == "comprobante_domicilio" and doc.get("fecha_emision"):
            dias = (hoy - doc["fecha_emision"]).days
            if dias > VIGENCIA_DIAS["comprobante_domicilio"]:
                factores.append(Factor("doc_expired", 20, False, f"Comprobante de domicilio con {dias} días de antigüedad."))
        if doc["doc_type"] == "csf" and doc.get("fecha_emision"):
            if (doc["fecha_emision"].year, doc["fecha_emision"].month) != (hoy.year, hoy.month):
                factores.append(Factor("csf_stale", 25, False, "La CSF no corresponde al mes calendario vigente."))
        if doc["doc_type"] == "manifestacion_protesta" and not fields.get("declara_no_69b_49bis"):
            factores.append(Factor("manifestacion_incompleta", 20, False, "La Manifestación bajo Protesta no confirma la cláusula de los Art. 69-B / 49 Bis CFF."))

    acta = next((d for d in documentos if d["doc_type"] == "acta_constitutiva"), None)
    if acta and not socios:
        factores.append(Factor("socios_incompletos", 20, False, "El acta constitutiva está presente pero no se registraron socios/accionistas/beneficiario controlador."))

    rep_legal_doc = next((d for d in documentos if d["doc_type"] == "identificacion_rep_legal"), None)
    if rep_legal_doc and not (rep_legal_doc.get("fields") or {}).get("nombre_completo"):
        factores.append(Factor("rep_legal_incompleto", 15, False, "No se capturó el nombre completo del representante legal."))
    return factores
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: factores de completitud y vigencia documental"`

### Task 3.5: Agregador + umbrales de decisión

**Files:**
- Create: `backend/src/domain/scoring/engine.py`
- Test: `backend/src/tests/test_scoring_engine.py`

**Interfaces:**
- Consumes: `Factor` (Task 3.2)
- Produces: `ResultadoEvaluacion(score_total, decision, critical_blocks, factores)`, `evaluar(factores: list[Factor]) -> ResultadoEvaluacion` — **agregador que no conoce el detalle de ningún factor individual (Open/Closed): agregar un factor nuevo en `factors.py` nunca requiere tocar este archivo.**

- [ ] **Paso 1 — Test (los 3 casos de demo, ancla de todo el motor):**
```python
from domain.scoring.engine import evaluar
from domain.scoring.factors import Factor

def test_sin_factores_es_safe():
    assert evaluar([]).decision == "safe"

def test_50_puntos_es_review_required_caso_demo_2():
    r = evaluar([Factor("doc_expired", 20, False, "x"), Factor("disc_razon_social", 30, False, "y")])
    assert r.score_total == 50 and r.decision == "review_required"

def test_bloqueo_critico_fuerza_high_risk_sin_importar_score():
    assert evaluar([Factor("sat_69b_definitivo", 100, True, "x")]).decision == "high_risk"

def test_rfc_invalido_fuerza_piso_review_required():
    assert evaluar([Factor("rfc_formato_invalido", 60, False, "x")]).decision == "review_required"
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from dataclasses import dataclass
from domain.scoring.factors import Factor

UMBRAL_HIGH_RISK = 70
UMBRAL_REVIEW_REQUIRED = 30

@dataclass(frozen=True)
class ResultadoEvaluacion:
    score_total: int
    decision: str
    critical_blocks: list[str]
    factores: list[Factor]

def evaluar(factores: list[Factor]) -> ResultadoEvaluacion:
    score_total = sum(f.points for f in factores)
    critical_blocks = [f.factor_code for f in factores if f.is_critical_block]
    if critical_blocks:
        decision = "high_risk"
    elif any(f.factor_code == "rfc_formato_invalido" for f in factores):
        decision = "review_required"
    elif score_total >= UMBRAL_HIGH_RISK:
        decision = "high_risk"
    elif score_total >= UMBRAL_REVIEW_REQUIRED:
        decision = "review_required"
    else:
        decision = "safe"
    return ResultadoEvaluacion(score_total, decision, critical_blocks, factores)
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: agregador de score y umbrales de decision"`

### Task 3.6: Ciclo de vida (`needs_update`)

**Files:**
- Create: `backend/src/domain/scoring/lifecycle.py`
- Test: `backend/src/tests/test_lifecycle.py`

- [ ] **Paso 1 — Test:**
```python
from datetime import date
from domain.scoring.lifecycle import necesita_actualizacion

def test_cliente_reporta_cambio_siempre_dispara_needs_update():
    assert necesita_actualizacion([], None, date(2026, 6, 28), cliente_reporto_cambio=True) is True

def test_comprobante_vencido_dispara_needs_update():
    documentos = [{"doc_type": "comprobante_domicilio", "fecha_emision": date(2026, 1, 1)}]
    assert necesita_actualizacion(documentos, None, date(2026, 6, 28), cliente_reporto_cambio=False) is True

def test_expediente_limpio_no_necesita_actualizacion():
    documentos = [{"doc_type": "comprobante_domicilio", "fecha_emision": date(2026, 6, 1)}]
    assert necesita_actualizacion(documentos, date(2026, 6, 1), date(2026, 6, 28), cliente_reporto_cambio=False) is False
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
def necesita_actualizacion(documentos: list[dict], ultima_consulta_sat, hoy, cliente_reporto_cambio: bool) -> bool:
    if cliente_reporto_cambio:
        return True
    if ultima_consulta_sat and (hoy - ultima_consulta_sat).days > 90:
        return True
    for doc in documentos:
        if doc["doc_type"] == "comprobante_domicilio" and doc.get("fecha_emision") and (hoy - doc["fecha_emision"]).days > 90:
            return True
        if doc["doc_type"] == "csf" and doc.get("fecha_emision") and (doc["fecha_emision"].year, doc["fecha_emision"].month) != (hoy.year, hoy.month):
            return True
    return False
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: lifecycle needs_update"`

### Task 3.7: Acción sugerida (mapeo determinístico, no generado por LLM)

**Files:**
- Create: `backend/src/domain/scoring/acciones.py`
- Test: `backend/src/tests/test_acciones.py`

- [ ] **Paso 1 — Test:**
```python
from domain.scoring.acciones import acciones_para

def test_acciones_para_caso_demo_2_en_orden_sin_duplicar():
    acciones = acciones_para(["disc_razon_social", "doc_expired", "disc_razon_social"])
    assert acciones == ["Corregir la razón social para que coincida entre documentos.", "Actualizar comprobante de domicilio."]
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
ACCIONES_SUGERIDAS = {
    "doc_expired": "Actualizar comprobante de domicilio.",
    "csf_stale": "Solicitar Constancia de Situación Fiscal del mes vigente.",
    "disc_razon_social": "Corregir la razón social para que coincida entre documentos.",
    "disc_rfc": "Verificar y corregir el RFC declarado — no coincide entre documentos.",
    "disc_domicilio": "Conciliar el domicilio entre los documentos del expediente.",
    "disc_representante": "Confirmar el nombre del representante legal entre poder, identificación y formulario.",
    "doc_missing": "Cargar el documento faltante o registrar su metadata manualmente.",
    "rfc_formato_invalido": "Corregir el RFC — no cumple el formato esperado.",
    "sat_69b_definitivo": "No operar — el cliente está en el listado definitivo de EFOS.",
}

def acciones_para(factor_codes: list[str]) -> list[str]:
    vistos = []
    for code in factor_codes:
        accion = ACCIONES_SUGERIDAS.get(code)
        if accion and accion not in vistos:
            vistos.append(accion)
    return vistos
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: mapeo deterministico de acciones sugeridas"`

### Task 3.8: Endpoint de evaluación (orquestación — reconciliación todavía con valores inyectados, IA real llega en Fase 4)

**Files:**
- Create: `backend/src/services/evaluation_service.py`
- Create: `backend/src/api/routers/expedientes.py`
- Test: `backend/src/tests/test_evaluation_service.py`

**Interfaces:**
- Consumes: `factores_listas_sat`, `factores_discrepancias`, `factores_completitud`, `evaluar`, `necesita_actualizacion`, `acciones_para`, `consultar_rfc_en_listas`
- Produces: `evaluar_expediente(supabase_client, expediente_id, resultado_reconciliacion, hoy=None) -> dict`. **En esta tarea `resultado_reconciliacion` se inyecta como parámetro — Task 4.5 reemplaza eso por el cálculo real desde la conciliación semántica.**

- [ ] **Paso 1 — Test:**
```python
from datetime import date
from domain.reconciliation.reconcile import ResultadoConciliacion
from services.evaluation_service import evaluar_expediente

def test_evaluar_expediente_caso_demo_1_limpio(fake_supabase):
    fake_supabase.store["expedientes"] = [{"id": "exp-1", "rfc": "EKU9003173C9"}]
    fake_supabase.store["documentos"] = []
    fake_supabase.store["socios"] = []
    resultado_limpio = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, "exp-1", resultado_limpio, hoy=date(2026, 6, 28))
    assert salida["decision"] in ("safe", "review_required")  # con 0 documentos sube por doc_missing, no por listas SAT — confirma que SAT limpio no es lo que tira el score
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from datetime import date, datetime, timezone
from domain.scoring.factors import factores_listas_sat, factores_discrepancias, factores_completitud
from domain.scoring.engine import evaluar
from domain.scoring.lifecycle import necesita_actualizacion
from domain.scoring.acciones import acciones_para
from infrastructure.sat.lookup import consultar_rfc_en_listas

def evaluar_expediente(supabase_client, expediente_id: str, resultado_reconciliacion, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    expediente = supabase_client.table("expedientes").select("*").eq("id", expediente_id).execute().data[0]
    documentos = supabase_client.table("documentos").select("*").eq("expediente_id", expediente_id).execute().data
    socios = supabase_client.table("socios").select("*").eq("expediente_id", expediente_id).execute().data

    sat_hits = consultar_rfc_en_listas(supabase_client, expediente_id, expediente["rfc"])
    factores = factores_listas_sat(sat_hits) + factores_discrepancias(resultado_reconciliacion) + factores_completitud(documentos, socios, hoy)
    resultado = evaluar(factores)
    acciones = acciones_para([f.factor_code for f in resultado.factores])
    needs_update = necesita_actualizacion(documentos, None, hoy, cliente_reporto_cambio=False)

    supabase_client.table("evaluations").insert({
        "expediente_id": expediente_id, "score_total": resultado.score_total, "decision": resultado.decision,
        "critical_blocks": resultado.critical_blocks, "summary": {"acciones_sugeridas": acciones},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    supabase_client.table("expedientes").update({
        "decision": resultado.decision, "score_total": resultado.score_total,
        "status": "needs_update" if needs_update else "completed",
        "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", expediente_id).execute()

    return {"score_total": resultado.score_total, "decision": resultado.decision, "acciones_sugeridas": acciones, "needs_update": needs_update}
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** Router delgado `POST /expedientes/{id}/evaluate` que llama a `evaluar_expediente` (sin lógica propia, per SOLID) — completar junto con Task 4.5 cuando exista la reconciliación real, no antes.
- [ ] **Paso 6:** `git checkout -b feat/scoring-engine && git add -A && git commit -m "feat: motor de reglas completo con harness, conciliacion y lifecycle" && git push -u origin feat/scoring-engine` → PR.

## Fase 4 — Extracción IA real + conciliación semántica

### Task 4.1: Schemas Pydantic de extracción por `doc_type`

**Files:**
- Create: `backend/src/infrastructure/ai/schemas.py`
- Test: `backend/src/tests/test_ai_schemas.py`

**Interfaces:**
- Produces: `SCHEMA_REGISTRY: dict[str, type[BaseModel]]` (uno por `doc_type`, incluye `encargo_conferido`), `SimilarityResult(similarity: float, same_entity: bool, reasoning: str)`.

- [ ] **Paso 1 — Test:**
```python
import pytest
from pydantic import ValidationError
from infrastructure.ai.schemas import SCHEMA_REGISTRY, SimilarityResult

def test_csf_schema_acepta_campos_nulos():
    assert SCHEMA_REGISTRY["csf"](rfc=None, razon_social="X SA de CV").rfc is None

def test_similarity_result_rechaza_fuera_de_rango():
    with pytest.raises(ValidationError):
        SimilarityResult(similarity=1.5, same_entity=True, reasoning="x")

def test_encargo_conferido_tiene_su_propio_schema():
    schema = SCHEMA_REGISTRY["encargo_conferido"](rfc_agente_aduanal="ABC010101XX1", alcance="general", fecha_vigencia="2026-01-01")
    assert schema.rfc_agente_aduanal == "ABC010101XX1"
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from pydantic import BaseModel, Field

class CsfFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    domicilio_fiscal: str | None = None
    fecha_emision: str | None = None
    regimen_fiscal: str | None = None

class ActaConstitutivaFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    socios: list[dict] = Field(default_factory=list)

class ComprobanteDomicilioFields(BaseModel):
    domicilio: str | None = None
    fecha_emision: str | None = None

class IdentificacionRepLegalFields(BaseModel):
    nombre_completo: str | None = None
    fecha_vencimiento: str | None = None

class PoderNotarialFields(BaseModel):
    nombre_representante: str | None = None
    alcance: str | None = None

class EncargoConferidoFields(BaseModel):
    rfc_agente_aduanal: str | None = None
    alcance: str | None = None
    fecha_vigencia: str | None = None

class ManifestacionProtestaFields(BaseModel):
    declara_no_69b_49bis: bool = False

class SimilarityResult(BaseModel):
    similarity: float = Field(ge=0.0, le=1.0)
    same_entity: bool
    reasoning: str

SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "csf": CsfFields, "acta_constitutiva": ActaConstitutivaFields,
    "comprobante_domicilio": ComprobanteDomicilioFields, "identificacion_rep_legal": IdentificacionRepLegalFields,
    "poder_notarial": PoderNotarialFields, "encargo_conferido": EncargoConferidoFields,
    "manifestacion_protesta": ManifestacionProtestaFields,
}
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: schemas pydantic de extraccion por doc_type"`

### Task 4.2: Cliente Groq + extracción estructurada con harness

**Files:**
- Create: `backend/src/infrastructure/ai/groq_client.py`, `backend/src/infrastructure/ai/extract.py`
- Test: `backend/src/tests/test_extract.py`

**Interfaces:**
- Consumes: `call_with_harness` (3.1), `SCHEMA_REGISTRY` (4.1)
- Produces: `extraer_campos(supabase_client, doc_type: str, texto: str) -> dict`

- [ ] **Paso 1 — Test (Groq mockeado — nunca se llama red real en tests):**
```python
from unittest.mock import patch
from infrastructure.ai.extract import extraer_campos

def test_extraer_campos_usa_el_harness_y_cachea(fake_supabase):
    with patch("infrastructure.ai.extract.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"
        }
        r1 = extraer_campos(fake_supabase, "csf", "texto del documento")
        r2 = extraer_campos(fake_supabase, "csf", "texto del documento")
        assert r1 == r2
        assert mock_model.call_count == 1  # la 2da vino del cache del harness
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
# groq_client.py
import os
from langchain_groq import ChatGroq

MODEL_EXTRACCION = "llama-3.3-70b-versatile"  # confirmar el modelo mas capaz disponible en Groq al implementar

def get_groq_model():
    return ChatGroq(model=MODEL_EXTRACCION, temperature=0, api_key=os.environ["GROQ_API_KEY"])
```
```python
# extract.py
from infrastructure.ai.groq_client import get_groq_model
from infrastructure.ai.schemas import SCHEMA_REGISTRY
from infrastructure.ai.harness import call_with_harness

PROMPT_EXTRACCION = (
    "Eres un extractor de datos de documentos fiscales y legales mexicanos. "
    "Extrae SOLO lo que aparece literalmente en el texto. Si un campo no esta "
    "presente, devuelve null. Normaliza fechas a ISO 8601. No inventes RFCs ni "
    "datos que no esten en el texto.\n\nTexto del documento:\n{texto}"
)

def extraer_campos(supabase_client, doc_type: str, texto: str) -> dict:
    schema_cls = SCHEMA_REGISTRY[doc_type]
    def compute() -> dict:
        modelo = get_groq_model().with_structured_output(schema_cls)
        return modelo.invoke(PROMPT_EXTRACCION.format(texto=texto)).model_dump()
    return call_with_harness(supabase_client, "extraction", {"doc_type": doc_type, "texto": texto}, compute)
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: extraccion estructurada via Groq envuelta en harness"`

### Task 4.3: Extracción de texto nativo + fallback OCR

**Files:**
- Create: `backend/src/infrastructure/ai/pdf.py`
- Test: `backend/src/tests/test_pdf_extract.py`

**Interfaces:**
- Consumes: `infrastructure.ai.ocr.ocr_imagen` (Task 2.6)
- Produces: `extraer_texto(pdf_path: str) -> str`

- [ ] **Paso 1 — Test:**
```python
from unittest.mock import patch, MagicMock
from infrastructure.ai.pdf import extraer_texto

def test_extraer_texto_usa_capa_nativa_si_hay_suficiente_texto():
    with patch("infrastructure.ai.pdf.PdfReader") as mock_reader:
        pagina = MagicMock(); pagina.extract_text.return_value = "Constancia de Situación Fiscal " * 5
        mock_reader.return_value.pages = [pagina]
        assert "Constancia" in extraer_texto("fake.pdf")

def test_extraer_texto_cae_a_ocr_si_no_hay_capa_de_texto():
    with patch("infrastructure.ai.pdf.PdfReader") as mock_reader, \
         patch("infrastructure.ai.pdf.convert_from_path") as mock_convert, \
         patch("infrastructure.ai.pdf.ocr_imagen", return_value="texto via ocr"):
        pagina = MagicMock(); pagina.extract_text.return_value = ""
        mock_reader.return_value.pages = [pagina]
        mock_convert.return_value = [MagicMock()]
        assert extraer_texto("fake_escaneado.pdf") == "texto via ocr"
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from pypdf import PdfReader
from pdf2image import convert_from_path
from infrastructure.ai.ocr import ocr_imagen

UMBRAL_TEXTO_MINIMO = 20

def extraer_texto(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texto = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(texto.strip()) >= UMBRAL_TEXTO_MINIMO:
        return texto
    paginas = convert_from_path(pdf_path)
    return "\n".join(ocr_imagen(p) for p in paginas)
```
- [ ] **Paso 4:** `uv add pypdf` (si no quedó de Fase 2), pasa.
- [ ] **Paso 5:** `git commit -m "feat: extraccion de texto nativo con fallback a OCR"`

### Task 4.4: Conciliación semántica real (razón social / domicilio / representante)

**Files:**
- Create: `backend/src/infrastructure/ai/similarity.py`
- Test: `backend/src/tests/test_similarity.py`

**Interfaces:**
- Consumes: `call_with_harness`, `SimilarityResult`
- Produces: `comparar_semanticamente(supabase_client, campo: str, texto_a: str, texto_b: str) -> dict`

- [ ] **Paso 1 — Test (mismo patrón de mock que Task 4.2):**
```python
from unittest.mock import patch
from infrastructure.ai.similarity import comparar_semanticamente

def test_comparar_semanticamente_cachea_por_harness(fake_supabase):
    with patch("infrastructure.ai.similarity.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "similarity": 0.92, "same_entity": True, "reasoning": "Misma entidad, distinta puntuación."
        }
        r1 = comparar_semanticamente(fake_supabase, "razón social", "Corporativo X SA de CV", "Corporativo X")
        r2 = comparar_semanticamente(fake_supabase, "razón social", "Corporativo X SA de CV", "Corporativo X")
        assert r1 == r2
        assert mock_model.call_count == 1
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
from infrastructure.ai.groq_client import get_groq_model
from infrastructure.ai.schemas import SimilarityResult
from infrastructure.ai.harness import call_with_harness

PROMPT_SIMILARITY = (
    "Compara estas dos cadenas que representan {campo} de una empresa mexicana. "
    "Considera abreviaturas legales equivalentes (SA de CV = S.A. de C.V.), acentos, "
    "mayusculas y orden de tokens. No penalices diferencias puramente ortograficas.\n"
    "Texto A: {texto_a}\nTexto B: {texto_b}"
)

def comparar_semanticamente(supabase_client, campo: str, texto_a: str, texto_b: str) -> dict:
    def compute() -> dict:
        modelo = get_groq_model().with_structured_output(SimilarityResult)
        return modelo.invoke(PROMPT_SIMILARITY.format(campo=campo, texto_a=texto_a, texto_b=texto_b)).model_dump()
    return call_with_harness(supabase_client, "similarity", {"campo": campo, "texto_a": texto_a, "texto_b": texto_b}, compute)
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git commit -m "feat: conciliacion semantica real via Groq con harness"`

### Task 4.5: Endpoints de documentos + reconciliación real conectada al evaluate

**Files:**
- Create: `backend/src/infrastructure/storage/supabase_storage.py`, `backend/src/api/routers/documentos.py`, `backend/src/services/reconciliation_service.py`
- Modify: `backend/src/api/routers/expedientes.py` (de Task 3.8 — ahora con reconciliación real, no inyectada), `backend/src/main.py`
- Test: `backend/src/tests/test_documentos_router.py`, `backend/src/tests/test_reconciliation_service.py`

**Interfaces:**
- Consumes: `extraer_texto`, `extraer_campos`, `comparar_semanticamente`, `reconciliar` (3.3)
- Produces: `crear_signed_upload_url` (solo firma URLs), endpoint único `POST /documentos` que crea la fila para **ambos** caminos de intake (`entry_method='uploaded'` devuelve además `signed_url`; `entry_method='manual'` devuelve solo `documento_id` con `extraction_status='not_applicable'`, listo para `PATCH` directo sin pasar por `/extract`), `POST /documentos/{id}/extract`, `PATCH /documentos/{id}`; `reconciliar_expediente(supabase_client, expediente_id) -> ResultadoConciliacion`.

- [ ] **Paso 1 — Test de `reconciliar_expediente` (Groq mockeado):**
```python
from unittest.mock import patch
from services.reconciliation_service import reconciliar_expediente

def test_reconciliar_expediente_arma_los_3_pares_y_aplica_umbral(fake_supabase):
    fake_supabase.store["expedientes"] = [{"id": "exp-1", "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV", "domicilio_fiscal": "Av X 123", "representante_legal": "Juan Pérez"}]
    fake_supabase.store["documentos"] = [{"doc_type": "csf", "fields": {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"}}]
    with patch("infrastructure.ai.similarity.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {"similarity": 1.0, "same_entity": True, "reasoning": "x"}
        resultado = reconciliar_expediente(fake_supabase, "exp-1")
    assert resultado.rfc_discrepante is False
    assert resultado.razon_social_discrepante is False
```
- [ ] **Paso 2:** falla.
    - [x] **Paso 3 — Implementación:**
      - Creado `backend/src/api/deps.py` con `get_supabase_client()`
      - Reemplazado `backend/src/api/routers/admin.py` — endpoint `POST /admin/sat/ingest/{list_type}`
      - `main.py` ya incluía el router, sin cambios necesarios
```python
# services/reconciliation_service.py
from domain.reconciliation.reconcile import reconciliar
from infrastructure.ai.similarity import comparar_semanticamente

def reconciliar_expediente(supabase_client, expediente_id: str):
    expediente = supabase_client.table("expedientes").select("*").eq("id", expediente_id).execute().data[0]
    documentos = {d["doc_type"]: d for d in supabase_client.table("documentos").select("*").eq("expediente_id", expediente_id).execute().data}

    rfcs = [expediente["rfc"]] + [
        (documentos[dt].get("fields") or {}).get("rfc", expediente["rfc"])
        for dt in ("csf", "acta_constitutiva", "rfc") if dt in documentos
    ]
    razon_social_csf = (documentos.get("csf", {}).get("fields") or {}).get("razon_social", expediente["razon_social"])
    sim_razon_social = comparar_semanticamente(supabase_client, "razón social", expediente["razon_social"], razon_social_csf)

    domicilio_comprobante = (documentos.get("comprobante_domicilio", {}).get("fields") or {}).get("domicilio", expediente["domicilio_fiscal"] or "")
    sim_domicilio = comparar_semanticamente(supabase_client, "domicilio", expediente["domicilio_fiscal"] or "", domicilio_comprobante)

    rep_poder = (documentos.get("poder_notarial", {}).get("fields") or {}).get("nombre_representante", expediente["representante_legal"] or "")
    sim_representante = comparar_semanticamente(supabase_client, "nombre de representante legal", expediente["representante_legal"] or "", rep_poder)

    return reconciliar(rfcs, sim_razon_social, sim_domicilio, sim_representante, fechas_validas=True)
```
```python
# infrastructure/storage/supabase_storage.py — responsabilidad unica: firmar URLs, no crea filas
def crear_signed_upload_url(supabase_client, path: str) -> dict:
    resp = supabase_client.storage.from_("kyb-docs").create_signed_upload_url(path)
    return {"signed_url": resp["signed_url"], "token": resp.get("token")}
```
```python
# api/routers/documentos.py — un solo endpoint de creacion cubre ambos caminos de intake
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.deps import get_supabase_client
from infrastructure.storage.supabase_storage import crear_signed_upload_url
from infrastructure.ai.pdf import extraer_texto
from infrastructure.ai.extract import extraer_campos

router = APIRouter(prefix="/documentos", tags=["documentos"])

class CrearDocumentoBody(BaseModel):
    expediente_id: str
    doc_type: str
    entry_method: str  # "uploaded" | "manual"

@router.post("")
def crear_documento(body: CrearDocumentoBody, supabase=Depends(get_supabase_client)):
    documento_id = str(uuid.uuid4())
    path = f"{body.expediente_id}/{body.doc_type}.pdf" if body.entry_method == "uploaded" else None
    supabase.table("documentos").insert({
        "id": documento_id, "expediente_id": body.expediente_id, "doc_type": body.doc_type,
        "entry_method": body.entry_method, "storage_path": path,
        "extraction_status": "pending" if body.entry_method == "uploaded" else "not_applicable",
    }).execute()
    if body.entry_method == "manual":
        return {"documento_id": documento_id}
    return {"documento_id": documento_id, **crear_signed_upload_url(supabase, path)}

@router.post("/{documento_id}/extract")
def extract_documento(documento_id: str, supabase=Depends(get_supabase_client)):
    doc = supabase.table("documentos").select("*").eq("id", documento_id).execute().data[0]
    texto = extraer_texto(doc["storage_path"])
    campos = extraer_campos(supabase, doc["doc_type"], texto)
    supabase.table("documentos").update({"extracted_raw": campos, "fields": campos, "extraction_status": "extracted"}).eq("id", documento_id).execute()
    return {"extraction_status": "extracted", "fields": campos}

@router.patch("/{documento_id}")
def revisar_documento(documento_id: str, fields: dict, supabase=Depends(get_supabase_client)):
    # Cubre ambos caminos: si el documento es entry_method='manual' (sin archivo),
    # este es el UNICO paso que toca, nunca pasó por /extract.
    supabase.table("documentos").update({"fields": fields, "extraction_status": "human_reviewed"}).eq("id", documento_id).execute()
    return {"extraction_status": "human_reviewed"}
```
```python
# api/routers/expedientes.py — Task 3.8 quedó con reconciliacion inyectada; ahora se completa:
from services.reconciliation_service import reconciliar_expediente

@router.post("/{expediente_id}/evaluate")
def evaluate(expediente_id: str, supabase=Depends(get_supabase_client)):
    resultado_reconciliacion = reconciliar_expediente(supabase, expediente_id)
    return evaluar_expediente(supabase, expediente_id, resultado_reconciliacion)

@router.post("/{expediente_id}/report-change")
def report_change(expediente_id: str, reason: str, supabase=Depends(get_supabase_client)):
    supabase.table("expedientes").update({"status": "needs_update", "needs_update_reason": reason}).eq("id", expediente_id).execute()
    supabase.table("audit_log").insert({"expediente_id": expediente_id, "event_type": "report_change", "payload": {"reason": reason}}).execute()
    return {"status": "needs_update"}
```
    - [x] **Paso 4:** pasa (34/34 tests — 32 baseline + 2 nuevos).
- [ ] **Paso 5:** `git checkout -b feat/ai-extraction && git add -A && git commit -m "feat: extraccion IA con harness, OCR fallback y conciliacion semantica real" && git push -u origin feat/ai-extraction` → PR.

## Fase 5 — UI / Dashboard

Esta fase prioriza verificación visual en `pnpm dev` por sobre TDD estricto de componentes (ya documentado como la fase recortable si el tiempo aprieta) — el código de cada paso es real y completo, no placeholder, pero el "paso de test" es "correr y mirar", no `vitest`.

### Task 5.1: Theme (`DESIGN-clickhouse.md`) + instalación de componentes shadcn

**Decisión de arquitectura de theming (verificado contra `ui.shadcn.com/docs/theming`):** shadcn/ui NO lee colores desde `tailwind.config.ts` para sus propios componentes. Cada componente instalado por el CLI (`Button`, `Badge`, `Card`, `Dialog`, etc.) usa clases semánticas (`bg-primary`, `bg-card`, `border-input`, `bg-destructive`...) que resuelven contra **variables CSS** definidas en `:root`/`.dark` del archivo de estilos global que genera `shadcn init` (típicamente `app/globals.css`, a confirmar el nombre/selector exactos contra lo que el CLI con `-b base` generó en el Paso 2 de la Fase 1 — Base UI puede diferir del layout de Radix). Tailwind solo expone esas variables como utilidades (`@theme inline` o mapeo en `tailwind.config.ts`, según versión de Tailwind detectada).

Por eso la versión anterior de esta tarea estaba mal: definía `primary: "#faff69"` como un color nuevo de Tailwind, en paralelo a las variables que los componentes reales consumen. Esto sí pinta un `<div className="bg-canvas">` escrito a mano, pero CUALQUIER componente shadcn instalado (el `Button` de un formulario, el `Badge` del semáforo) seguiría usando la paleta default de shadcn — exactamente el problema de mantenibilidad que querías evitar (cambiar un color en un solo lugar y que cascadee a todo).

**Corrección — la paleta se inyecta sobreescribiendo las variables CSS existentes, no como un sistema de colores paralelo:**

- [ ] **Paso 1:** Abrir el archivo de estilos global que generó `shadcn init -b base` en el Paso 2 de la Fase 1 (confirmar la ruta exacta — no asumir `app/globals.css` sin mirarlo) y localizar el bloque `:root { --background: ...; --foreground: ...; --primary: ...; --card: ...; --border: ...; --input: ...; --ring: ...; --radius: ...; ... }`. Confirmar también el formato de color que usa (HSL vs `oklch()` — difiere por versión de Tailwind/shadcn) antes de escribir ningún valor nuevo.
- [ ] **Paso 2:** Traducir la paleta de `DESIGN-clickhouse.md` al formato detectado en el Paso 1 y **sobreescribir los tokens semánticos existentes** (no inventar nombres nuevos para estos):
  - `--background` → `#0a0a0a` (canvas)
  - `--foreground` → blanco/texto principal
  - `--card` / `--popover` → `#1a1a1a` (surface-card)
  - `--primary` → `#faff69` (amarillo eléctrico), `--primary-foreground` → `#0a0a0a` (texto oscuro sobre fondo amarillo)
  - `--border` / `--input` / `--ring` → `#2a2a2a` (hairline)
  - `--muted` / `--muted-foreground` → grises de `DESIGN-clickhouse.md`
  - `--destructive` → `#ef4444` (accent-rose, también reutilizado para `high_risk`)
  - `--radius` → `0.5rem` (8px, cubre botones/inputs vía la cadena `--radius-sm/md/lg` que el CLI ya deriva)
- [ ] **Paso 3:** Para conceptos que shadcn NO tiene por default (semáforo `safe`/`review_required` necesita éxito/advertencia, no solo `destructive`; `surface-elevated`; tipografía `stat-display`), **agregar** variables CSS nuevas siguiendo el mismo mecanismo — nunca como hex crudo en `theme.extend`:
  ```css
  :root {
    --success: 142 71% 45%;   /* #22c55e, accent-emerald — safe */
    --warning: 38 92% 50%;    /* #f59e0b — review_required */
    --surface-elevated: 0 0% 14%; /* #242424 */
  }
  ```
  y exponerlas en `tailwind.config.ts` (o el bloque `@theme inline` si el proyecto quedó en Tailwind v4) de la misma forma en que el CLI expone `--primary`:
  ```typescript
  colors: {
    success: "hsl(var(--success))",
    warning: "hsl(var(--warning))",
    "surface-elevated": "hsl(var(--surface-elevated))",
  }
  ```
  (ajustar `hsl(var(...))` a `var(...)` directo si el Paso 1 confirmó que el proyecto usa `oklch()` en vez de HSL).
- [ ] **Paso 4:** Fuentes (`Inter`/`JetBrains Mono`) y radii por capa (8px botones/inputs ya cubierto por `--radius` en el Paso 2; 12px cards vía una variable adicional `--radius-card` si el componente `Card` no lo permite por props) — agregar a `tailwind.config.ts` `fontFamily` como extend normal (esto sí es seguro como extend directo, no es un token que los componentes shadcn ya usen internamente para decidir su propio color).
- [ ] **Paso 5:**
```bash
pnpm dlx shadcn@latest add dashboard-01 item field empty skeleton spinner button-group input-group kbd attachment shimmer marker badge card tabs resizable chart accordion tooltip data-table sidebar breadcrumb command sonner alert alert-dialog dialog separator hover-card progress select textarea label input button
```
- [ ] **Paso 6 — Verificación real (más estricta que la versión anterior):** `pnpm dev`, renderizar un `<Button>` y un `<Badge>` de shadcn (no un `<div>` escrito a mano) en una página de prueba y confirmar en devtools que `background-color` resuelve a `#faff69`/`#0a0a0a` — esto prueba que el cascade funciona sobre componentes reales, no solo sobre clases custom. Cambiar `--primary` a un valor de prueba y confirmar que el `Button` cambia sin tocar ningún archivo `.tsx`.
- [ ] **Paso 7:** `git commit -m "feat: theme clickhouse via variables CSS de shadcn + componentes base"`

### Task 5.2: Cliente API tipado

**Files:** Create `frontend/src/lib/api-client.ts`.
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL!;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export type Expediente = { id: string; razon_social: string; rfc: string; status: string; decision: "safe" | "review_required" | "high_risk" | null; score_total: number | null };

export const api = {
  listExpedientes: () => request<Expediente[]>("/expedientes"),
  getExpediente: (id: string) => request<Expediente>(`/expedientes/${id}`),
  createExpediente: (data: Partial<Expediente>) => request<Expediente>("/expedientes", { method: "POST", body: JSON.stringify(data) }),
  evaluate: (id: string) => request(`/expedientes/${id}/evaluate`, { method: "POST" }),
  crearDocumento: (expedienteId: string, docType: string, entryMethod: "uploaded" | "manual") =>
    request<{ documento_id: string; signed_url?: string }>("/documentos", { method: "POST", body: JSON.stringify({ expediente_id: expedienteId, doc_type: docType, entry_method: entryMethod }) }),
  extractDocumento: (documentoId: string) => request(`/documentos/${documentoId}/extract`, { method: "POST" }),
  reviewDocumento: (id: string, fields: Record<string, unknown>) => request(`/documentos/${id}`, { method: "PATCH", body: JSON.stringify({ fields }) }),
  reportChange: (id: string, reason: string) => request(`/expedientes/${id}/report-change`, { method: "POST", body: JSON.stringify({ reason }) }),
};
```
- [ ] `git commit -m "feat: cliente API tipado del frontend"`

### Task 5.3: Dashboard de expedientes

**Files:** Create `frontend/src/app/page.tsx`.
```tsx
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";

const DECISION_STYLE: Record<string, string> = {
  safe: "bg-accent-emerald text-canvas", review_required: "bg-warning text-canvas", high_risk: "bg-accent-rose text-canvas",
};

export default async function DashboardPage() {
  const expedientes = await api.listExpedientes();
  return (
    <main className="bg-canvas min-h-screen p-8 text-white">
      <h1 className="text-3xl font-bold mb-6">Expedientes KYB</h1>
      <table className="w-full text-sm">
        <thead className="text-muted"><tr><th className="text-left py-2">Cliente</th><th>RFC</th><th>Estatus</th><th>Score</th></tr></thead>
        <tbody>
          {expedientes.map((e) => (
            <tr key={e.id} className="border-t border-hairline">
              <td className="py-2"><a href={`/expedientes/${e.id}`}>{e.razon_social}</a></td>
              <td>{e.rfc}</td>
              <td>{e.decision && <Badge className={DECISION_STYLE[e.decision]}>{e.decision}</Badge>}</td>
              <td>{e.score_total ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```
Nota: migrar este contenido dentro del block `dashboard-01` instalado en 5.1 una vez que haya datos reales corriendo — confirmar su composición exacta (`frontend/src/components/dashboard-01/`) leyendo el código que el CLI copió, no adivinando su API.
- [ ] Verificar visualmente contra el backend desplegado. `git commit -m "feat: dashboard de expedientes"`

### Task 5.4: Alta de expediente

**Files:** Create `frontend/src/app/expedientes/nuevo/page.tsx`.
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function NuevoExpedientePage() {
  const router = useRouter();
  const [form, setForm] = useState({ razon_social: "", rfc: "", domicilio_fiscal: "", representante_legal: "" });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const expediente = await api.createExpediente(form);
    router.push(`/expedientes/${expediente.id}`);
  }

  return (
    <form onSubmit={onSubmit} className="bg-canvas min-h-screen p-8 text-white space-y-4 max-w-md">
      <div><label className="block text-sm mb-1">Razón social</label><Input value={form.razon_social} onChange={(e) => setForm({ ...form, razon_social: e.target.value })} required /></div>
      <div><label className="block text-sm mb-1">RFC</label><Input value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value.toUpperCase() })} required /></div>
      <div><label className="block text-sm mb-1">Domicilio fiscal</label><Input value={form.domicilio_fiscal} onChange={(e) => setForm({ ...form, domicilio_fiscal: e.target.value })} /></div>
      <div><label className="block text-sm mb-1">Representante legal</label><Input value={form.representante_legal} onChange={(e) => setForm({ ...form, representante_legal: e.target.value })} /></div>
      <Button type="submit" className="bg-primary text-canvas">Crear expediente</Button>
    </form>
  );
}
```
Nota: migrar los `<div><label>` a `Field`/`FieldLabel` (instalado en 5.1) leyendo `frontend/src/components/ui/field.tsx` real, no la API adivinada.
- [ ] Verificar visualmente, crear un expediente de prueba contra el backend. `git commit -m "feat: formulario de alta de expediente"`

### Task 5.5: Subida de documentos — los dos caminos de intake

**Files:** Create `frontend/src/components/DocumentUploader.tsx`.
```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = { expedienteId: string; docType: string };
type Estado = "idle" | "uploading" | "processing" | "done" | "error";

export function DocumentUploader({ expedienteId, docType }: Props) {
  const [modo, setModo] = useState<"archivo" | "manual">("archivo");
  const [estado, setEstado] = useState<Estado>("idle");

  async function subirArchivo(file: File) {
    setEstado("uploading");
    try {
      const { documento_id, signed_url } = await api.crearDocumento(expedienteId, docType, "uploaded");
      await fetch(signed_url!, { method: "PUT", body: file });
      setEstado("processing");
      await api.extractDocumento(documento_id);
      setEstado("done");
    } catch {
      setEstado("error");
    }
  }

  async function capturarManual() {
    const { documento_id } = await api.crearDocumento(expedienteId, docType, "manual");
    window.location.href = `/expedientes/${expedienteId}/revisar?documento_id=${documento_id}`;
  }

  return (
    <div className="border border-hairline rounded-lg p-4 bg-surface-card">
      <div className="flex gap-2 mb-3">
        <Button variant={modo === "archivo" ? "default" : "outline"} onClick={() => setModo("archivo")}>Subir archivo</Button>
        <Button variant={modo === "manual" ? "default" : "outline"} onClick={() => setModo("manual")}>Capturar sin archivo</Button>
      </div>
      {modo === "archivo" ? (
        <Input type="file" accept="application/pdf" onChange={(e) => e.target.files?.[0] && subirArchivo(e.target.files[0])} />
      ) : (
        <Button onClick={capturarManual} className="bg-primary text-canvas">Crear registro manual</Button>
      )}
      <p className="text-xs text-muted mt-2">Estado: {estado}</p>
    </div>
  );
}
```
Nota: reemplazar el bloque de estado por el componente real `Attachment` (props exactos a confirmar en `frontend/src/components/ui/attachment.tsx` instalado en 5.1) — el mapeo conceptual `idle/uploading/processing/done/error` ya coincide 1:1 con `extraction_status`.
- [ ] Verificar ambos caminos contra el backend real. `git commit -m "feat: subida de documentos con los dos caminos de intake"`

### Task 5.6: Visualización en vivo del pipeline de Harness

**Files:** Create `frontend/src/components/PipelineStatus.tsx`.
```tsx
const PASOS = ["Extrayendo texto del PDF", "Validando contra esquema", "Consultando listas del SAT", "Calculando score"] as const;

export function PipelineStatus({ pasoActual }: { pasoActual: number }) {
  return (
    <ul className="space-y-2">
      {PASOS.map((paso, i) => (
        <li key={paso} className={i === pasoActual ? "text-primary animate-pulse" : i < pasoActual ? "text-accent-emerald" : "text-muted"}>
          {i < pasoActual ? "✓ " : "› "}{paso}{i === pasoActual ? "…" : ""}
        </li>
      ))}
    </ul>
  );
}
```
Nota: reemplazar la animación CSS ad-hoc por `Marker`+`Shimmer` reales (instalados en 5.1) una vez confirmada su API — esto es el placeholder funcional mínimo que ya comunica el concepto correctamente.
- [ ] `git commit -m "feat: visualizacion en vivo del pipeline de extraccion/evaluacion"`

### Task 5.7: Revisión humana de extracción (panel dividido)

**Files:** Create `frontend/src/app/expedientes/[id]/revisar/page.tsx`.
```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export default function RevisarPage({ params }: { params: { id: string } }) {
  const [fields, setFields] = useState<Record<string, string>>({});

  async function confirmar(documentoId: string) {
    await api.reviewDocumento(documentoId, fields);
  }

  return (
    <div className="bg-canvas min-h-screen text-white grid grid-cols-2 gap-4 p-8">
      <div className="bg-surface-card rounded-lg p-4">
        <p className="text-muted text-sm">Preview del PDF original (iframe al signed URL de Storage)</p>
      </div>
      <div className="bg-surface-card rounded-lg p-4 space-y-3">
        {Object.entries(fields).map(([campo, valor]) => (
          <div key={campo}>
            <label className="block text-sm mb-1">{campo}</label>
            <Textarea value={valor} onChange={(e) => setFields({ ...fields, [campo]: e.target.value })} />
          </div>
        ))}
        <Button onClick={() => confirmar(params.id)} className="bg-primary text-canvas">Confirmar revisión</Button>
      </div>
    </div>
  );
}
```
Nota: el `grid grid-cols-2` es el placeholder del componente `resizable` real (5.1) — panel ajustable es deseable, no bloqueante; confirmar API de `ResizablePanelGroup` contra el archivo instalado antes de migrar.
- [ ] Verificar el flujo completo: extraer → revisar → confirmar → el dato llega a `documentos.fields` con `human_reviewed`. `git commit -m "feat: pantalla de revision humana de extraccion"`

### Task 5.8: Reporte de score explicable

**Files:** Create `frontend/src/app/expedientes/[id]/reporte/page.tsx`.
```tsx
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";

export default async function ReportePage({ params }: { params: { id: string } }) {
  const expediente = await api.getExpediente(params.id);
  return (
    <div className="bg-canvas min-h-screen text-white p-8">
      <h1 className="text-2xl font-bold mb-2">{expediente.razon_social}</h1>
      <Badge className="mb-4">{expediente.decision}</Badge>
      <p className="text-5xl font-bold text-primary mb-6">{expediente.score_total ?? 0} pts</p>
      {/* Lista de factores_score + acciones_sugeridas via un fetch adicional GET /expedientes/{id}/evaluations/latest — completar endpoint si no existe ya en Fase 3/4 */}
    </div>
  );
}
```
Nota: el dato `factores_score`/`acciones_sugeridas` necesita un endpoint `GET /expedientes/{id}/evaluations/latest` que no se nombró explícito en Fase 3/4 — agregarlo como parte de esta tarea (router delgado, reusa `evaluations` ya persistida, sin lógica nueva). El componente `chart` (donut con score al centro) se conecta una vez ese endpoint exista.
- [ ] Verificar que coincide exactamente con los 3 casos de demo. `git commit -m "feat: reporte de score explicable"`

### Task 5.9: Admin SAT + audit log visible

**Files:** Create `frontend/src/app/admin/page.tsx`, `frontend/src/app/expedientes/[id]/page.tsx` (tab de audit log).
- [ ] Botón "Actualizar listas SAT" por cada `list_type`, llamando al endpoint admin de Task 2.7, mostrando `rows_imported` y fecha de la última corrida exitosa (`sat_import_runs`).
- [ ] Tab "Audit log" en el detalle del expediente listando `consultas_sat` (fuente, fecha/hora, RFC, resultado, referencia al listado) — es el requisito explícito de auditoría del brief, visible, no solo guardado en BD.
- [ ] `git checkout -b feat/dashboard-ui && git add -A && git commit -m "feat: dashboard, alta, revision humana, reporte y admin completos" && git push -u origin feat/dashboard-ui` → PR.

## Fase 6 — Datos de demo, verificación final y entrega

### Task 6.1: Seed de los 3 expedientes de demo

**Files:** Create `backend/scripts/seed_demo.py` (script, no parte del paquete `src/`).
```python
import os
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

DEMO = [
    {"razon_social": "Escuela Kemper Urgate SA de CV", "rfc": "EKU9003173C9", "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma, CDMX", "representante_legal": "Juan Pérez García"},
    {"razon_social": "Corporativo X", "rfc": "COX010101AB1", "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma", "representante_legal": "María López"},
    # tercer RFC se completa con uno real del listado 69-B Definitivos vigente al momento de correr el seed — no hardcodear uno que pueda quedar desactualizado
]

for expediente in DEMO:
    supabase.table("expedientes").insert(expediente).execute()
```
- [ ] **Paso 1:** Antes de correr el seed, ejecutar el ETL real (Task 2.7) contra las 3 fuentes del SAT.
- [ ] **Paso 2:** Tomar un RFC real y vigente del listado `art_69b` con `art69b_substate='definitivo'` recién importado, completar el tercer registro de `DEMO`.
- [ ] **Paso 3:** Correr `uv run python scripts/seed_demo.py`.
- [ ] **Paso 4:** `git commit -m "feat: seed de los 3 expedientes de demo"`

### Task 6.2: Generación de los 3 expedientes sintéticos completos (documentos)

No es código — es la instrucción operativa para esta tarea, ya decidida en secciones anteriores:
- [ ] Generar los PDFs de cada documento (acta, CSF, comprobante, identificación, poder/encargo conferido, manifestación) con **texto seleccionable** (Word/LaTeX/HTML→PDF, nunca una imagen escaneada — ver Task 2.6).
- [ ] Expediente 1 (limpio): datos consistentes con `EKU9003173C9`, fechas vigentes (CSF del mes actual, comprobante <90 días).
- [ ] Expediente 2 (review_required): comprobante de domicilio con fecha de >90 días de antigüedad + razón social "Corporativo X" en el formulario vs "Corporativo X SA de CV" en la CSF — replica el ejemplo textual del brief.
- [ ] Expediente 3 (high_risk): usar el RFC real confirmado en Task 6.1 Paso 2; los documentos pueden ser mínimos (el bloqueo es por listas SAT, no por completitud documental).
- [ ] Subir los documentos de cada expediente vía la UI real (Task 5.5), confirmar extracción + revisión humana, evaluar.

### Task 6.3: Verificación end-to-end final

Ya especificada en la sección "Verificación end-to-end" de este documento — ejecutar los 5 puntos contra el deploy real, confirmando explícitamente las 3 clasificaciones esperadas (`safe`/`review_required`/`high_risk`) de los expedientes de Task 6.2.

### Task 6.4: README

**Files:** Create `README.md` (raíz del repo).
Debe incluir, sin excepción: (a) cómo correr local (`uv` + `pnpm`), (b) arquitectura de dos servicios y por qué, (c) la rúbrica de scoring completa (copiada de este plan), (d) las limitaciones documentadas a propósito — Art. 49 Bis sin lista pública, resultado del spike de OCR (Task 2.6), VUCEM/Opinión de Cumplimiento fuera de alcance —, (e) cómo se usó IA y por qué el veredicto final sigue siendo determinístico (harness engineering), (f) link a este plan y al transcript de la conversación.
- [ ] `git commit -m "docs: README completo de arquitectura y decisiones"`

### Task 6.5: Deploy final y entrega

- [ ] Confirmar ambos proyectos de Vercel en producción, URLs públicas accesibles sin login.
- [ ] Confirmar repo de GitHub público.
- [ ] Exportar el transcript de esta conversación a JSONL o Markdown.
- [ ] Responder al correo original de Pedro Ríos con los 3 entregables, antes del domingo 28/06/2026 4:45pm.
- [ ] `git checkout -b feat/demo-data && git add -A && git commit -m "feat: datos de demo, README y verificacion final" && git push -u origin feat/demo-data` → PR final hacia `main`.

---

## Próximos pasos inmediatos tras la aprobación de este plan

Modo-plan restringe a un solo archivo editable — estas acciones se ejecutan en cuanto se aprueba, en este orden:

1. **Partir este documento** en `docs/superpowers/plans/2026-06-27-<fase>.md` por fase (6 archivos), siguiendo la convención exacta de la skill `writing-plans` — este archivo único queda como el documento de arquitectura/contexto (todo lo anterior a "Plan granular de implementación"), no como el plan ejecutable final.
2. **Generar `CLAUDE.md`** en la raíz del repo (vía la skill `init`) con: stack y arquitectura de dos servicios, principios no negociables (harness engineering, SOLID/KISS, determinismo del motor de reglas), convención `uv`/`pnpm` exclusiva, comandos de test (`pytest` backend, verificación visual frontend), y referencia a este plan — el objetivo explícito de "no olvidar nada de lo planificado" se cumple con este archivo más que con cualquier otra cosa, porque es lo primero que se carga en cada sesión futura.
3. **Elegir modalidad de ejecución** (pregunta de la skill `writing-plans`, pendiente de tu respuesta): **Subagent-Driven** (un subagente fresco por tarea, revisión entre tareas — recomendado dado el tamaño de este plan) o **Inline Execution** (ejecutar en esta misma sesión con `executing-plans`, lotes con checkpoints).
4. Empezar por **Fase 1, Task 1.1**, en una rama `feat/scaffolding` — recién ahí se escribe la primera línea de código real de este proyecto.
