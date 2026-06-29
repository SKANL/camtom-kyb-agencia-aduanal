# CLAUDE.md

## Proyecto

Plataforma KYB (Know Your Business) para una agencia aduanal — prueba técnica de Software Engineer para Camtom. Deadline: domingo 28/06/2026 4:45pm (48h naturales desde la recepción del correo). El sistema determina si una persona moral mexicana es `safe`, `review_required` o `high_risk` para operar comercio exterior, cumpliendo la Regla 1.4.14 RGCE 2026.

## Plan de implementación

El plan completo (arquitectura, modelo de datos, rúbrica de scoring exacta, y el desglose granular TDD por fase con código real y comandos) vive en `docs/superpowers/plans/2026-06-27-kyb-agencia-aduanal.md`. **Leerlo completo antes de tocar código** — está escrito en formato `superpowers:writing-plans` (tareas con checkboxes, archivos exactos, código completo, sin placeholders). No se resume bien; las decisiones de arquitectura tienen razones específicas documentadas ahí, no las repitas de memoria.

## Estructura del monorepo (regla de orden, no negociable)

Todo el código vive en `frontend/` o `backend/`. La raíz del repo solo contiene: `CLAUDE.md`, la carpeta `docs/`, y configs de tooling que por convención van ahí (`.gitignore`, `.mcp.json`). Nada de código, specs de app ni assets sueltos en la raíz.

- `DESIGN-clickhouse.md` (spec del sistema de diseño) vive en `frontend/DESIGN-clickhouse.md`. Hoy está en la raíz solo temporalmente; la Fase 1 lo mueve a `frontend/` justo después de `create-next-app` (ese comando no corre si el directorio destino ya tiene archivos no reconocidos).
- Los artefactos npm de la raíz (`package.json`, `package-lock.json`, `node_modules/`) son solo del MCP de shadcn (`.mcp.json` → `npx shadcn@latest mcp`) y están gitignoreados — no son dependencias de la app, no confundir con las del `frontend/`.

## Variables de entorno

Cada proyecto tiene su propio `.env.example` (contenido exacto definido en el plan, Fase 1 Pasos 2.2 y 3.1; no se pre-crearon porque `create-next-app` aborta con archivos fuera de su whitelist y hay un guard de permisos sobre archivos `.env*`). El usuario crea el `.env` real (`backend/.env`) / `.env.local` (`frontend/.env.local`) a partir del ejemplo. `backend/` necesita `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`; `frontend/` necesita solo `NEXT_PUBLIC_API_URL` (la URL del backend, conocida recién tras su deploy). Todos los `.env`/`.env.local` reales están gitignoreados; solo los `.env.example` se trackean. Nunca escribir secretos en archivos trackeados.

## Arquitectura (resumen — el plan tiene el detalle completo)

- Monorepo: `frontend/` (Next.js App Router + TypeScript + Tailwind + shadcn/ui con estilo `-b base` + Zustand) y `backend/` (FastAPI + Python), cada uno desplegado como proyecto Vercel separado.
- El backend es dueño único de datos, lógica de negocio e IA — accede a Supabase (Postgres + Storage) vía el cliente `supabase-py` directo, sin ORM (SQLAlchemy descartado por YAGNI). El frontend nunca toca Supabase directo, solo llama al backend por REST.
- IA: LangChain (Python) + `langchain-groq`. **El LLM nunca decide la clasificación final** — solo produce métricas (`similarity`, `same_entity`) que un motor de reglas en Python puro interpreta con umbrales fijos. Toda llamada a IA pasa por una capa de Harness (`infrastructure/ai/harness.py`) con caché de idempotencia por hash — esto es "harness engineering": el modelo es un componente no confiable encapsulado dentro de un sistema determinístico.
- Listas fiscales del SAT (Art. 69, 69-B, 69-B Bis) se descargan vía ETL a una tabla local (`sat_lista_registros`); toda consulta en tiempo de evaluación es contra esa tabla, nunca contra el sitio del SAT. El Art. 49 Bis no tiene lista pública — se documenta como limitación conocida, no se inventa una fuente.
- Sin autenticación en el demo público (decisión consciente, no descuido).

## Convenciones no negociables

- **Python 3.13** en el backend — pineado con `backend/.python-version` (`3.13`) + `requires-python = ">=3.13"` (`uv init backend --python 3.13`). Soportado por Vercel (3.12/3.13/3.14) y matchea el local instalado, sin version-skew.
- `uv` exclusivo en `backend/` — nunca pip/poetry, nunca editar `pyproject.toml` a mano (`uv init`, `uv add <pkg>`, `uv export --format requirements.txt` para el build de Vercel).
- **Supabase solo online (cloud)** — nunca `supabase start` ni stack Docker local. Migraciones versionadas en `supabase/migrations/`, aplicadas al proyecto cloud con `supabase link` + `supabase db push`; fallback = SQL Editor del dashboard.
- `pnpm` exclusivo en `frontend/` — nunca npm/yarn/npx. (El `package.json`/`node_modules` en la raíz del repo son del MCP de shadcn, no de la app — no tocar ni confundir con dependencias del frontend.)
- Si existe un comando oficial para scaffoldear algo, usarlo — no escribir a mano lo que un CLI ya genera (`create-next-app`, `shadcn init/add`, `uv init`, `supabase migration new`).
- TDD estricto en el backend: test primero, verlo fallar, implementar lo mínimo, verlo pasar, commit. Cero placeholders ni "TODO" — si el plan no especifica el código completo de un paso, es un gap a resolver antes de avanzar, no a improvisar.
- Feature Branch Workflow: `main` protegida, una rama por fase (`feat/scaffolding`, `feat/sat-etl`, `feat/scoring-engine`, `feat/ai-extraction`, `feat/dashboard-ui`, `feat/demo-data`), un PR por rama.
- Frontend (Fase 5) prioriza verificación visual (`pnpm dev`) sobre TDD estricto de componentes — es la fase recortable si el tiempo aprieta. Backend (Fases 2-4) es innegociable.

## Comandos

- Backend: `cd backend && uv run pytest src/tests/ -v` · `uv run fastapi dev src/main.py`
- Frontend: `cd frontend && pnpm dev` · `pnpm build`

## RTK — Rust Token Killer (Mandatory)

RTK is a CLI proxy that compresses command output by **60-90%** before it reaches the context window. Single Rust binary, zero dependencies, <10ms overhead. Open source (Apache 2.0), no telemetry by default.

**YOU MUST prefix EVERY supported CLI command with `rtk`**. This is not optional — the savings compound across every command in every session.

```
Without RTK:  git status  →  ~3,000 tokens
With RTK:     rtk git status  →  ~600 tokens  (80% saved)
```

### Installation & activation (Windows)

```powershell
# Via Cargo (si Rust está instalado):
cargo install --git https://github.com/rtk-ai/rtk

# Activar hook para Claude Code (hacer una sola vez):
rtk init -g

# Verificar:
rtk --version
rtk gain
rtk init --show
```

### Windows PowerShell — CLAUDE.md injection mode

El hook de auto-rewrite requiere shell Unix — **no funciona en PowerShell nativo**. Con `rtk init -g`, RTK cae en **CLAUDE.md injection mode**: los filtros funcionan al 100%, pero los comandos NO se reescriben solos. **Vos (el AI) tenés que agregar el prefijo `rtk` manualmente** en cada comando.

Adicionalmente, los built-in tools de Claude Code (`Read`, `Grep`, `Glob`) siempre bypass RTK sin importar la plataforma — solo los comandos Bash/shell pasan por RTK.

---

### Command reference — este proyecto

#### Git

| En vez de | Usar | Ahorro |
|---|---|---|
| `git status` | `rtk git status` | 80% |
| `git log -n 10` | `rtk git log -n 10` | 80% |
| `git diff` | `rtk git diff` | 75% |
| `git show` | `rtk git show` | 75% |
| `git stash list` | `rtk git stash list` | 75% |
| `git add .` | `rtk git add .` | → `ok` |
| `git commit -m "msg"` | `rtk git commit -m "msg"` | → `ok abc1234` |
| `git push` | `rtk git push` | → `ok main` |
| `git pull` | `rtk git pull` | → `ok 3 files +10 -2` |

#### GitHub CLI

| En vez de | Usar | Ahorro |
|---|---|---|
| `gh pr view 42` | `rtk gh pr view 42` | 87% |
| `gh pr checks` | `rtk gh pr checks` | 79% |
| `gh run list` | `rtk gh run list` | 82% |
| `gh issue list` | `rtk gh issue list` | 80% |
| `gh pr list` | `rtk gh pr list` | Compact |

#### Python — backend (`uv`, `pytest`, `ruff`, `mypy`)

| En vez de | Usar | Ahorro |
|---|---|---|
| `uv run pytest src/tests/ -v` | `rtk test "uv run pytest src/tests/ -v"` | ~90% (solo fallos) |
| `ruff check` | `rtk ruff check` | 75% |
| `mypy` | `rtk mypy` | 75% |
| `pip list` | `rtk pip list` | auto-detecta uv |

> `rtk pytest` mapea a `pytest` a secas. Para `uv run pytest`, usar el wrapper genérico `rtk test "<cmd>"` — muestra solo los fallos.

#### JavaScript / TypeScript — frontend (`pnpm`, Next.js)

| En vez de | Usar | Ahorro |
|---|---|---|
| `pnpm build` | `rtk next build` | 80% |
| `pnpm list` | `rtk pnpm list` | 70-90% |
| `pnpm outdated` | `rtk pnpm outdated` | 70% |
| `tsc --noEmit` | `rtk tsc` | 75% |
| `eslint .` | `rtk lint` | 84% |
| `prettier --check .` | `rtk prettier --check .` | Solo archivos con cambios |

#### Files y search

| En vez de | Usar | Ahorro |
|---|---|---|
| `ls -la` | `rtk ls .` | 80% |
| `cat <file>` | `rtk read <file>` | 60-80% |
| `grep <pattern>` | `rtk grep <pattern>` | ~50% |
| `find . -name "*.py"` | `rtk find "*.py"` | 75% |
| `diff file1 file2` | `rtk diff file1 file2` | 65% |
| `cat pyproject.toml` | `rtk deps` | 85% (resumen de deps) |
| Resumen de código | `rtk smart <file>` | 85% (heurística 2 líneas) |
| Solo firmas | `rtk read <file> -l aggressive` | 95% |

#### Logs y datos

| En vez de | Usar |
|---|---|
| `cat app.log` | `rtk log app.log` |
| `curl <url>` | `rtk curl <url>` |
| `cat config.json` | `rtk json config.json` |

#### Wrappers genéricos (catch-all)

```bash
# Cualquier comando de test — solo fallos (~90% ahorro):
rtk test "uv run pytest src/tests/ -v"

# Cualquier comando — solo errores:
rtk err <command>

# Comando sin soporte — passthrough con tracking:
rtk proxy <command>
```

---

### Ultra-compact mode

Usar `--ultra-compact` para reducción máxima (íconos ASCII, formato inline):

```bash
rtk ruff check --ultra-compact
rtk tsc --ultra-compact
```

> **Git caveat**: NO usar `-u` con comandos Git — Git interpreta `-u` como `--set-upstream`. Usar siempre la forma larga `--ultra-compact`.

---

### Analytics

```bash
rtk gain                          # dashboard — ahorro total
rtk gain --graph                  # gráfico ASCII (últimos 30 días)
rtk gain --history                # historial de comandos
rtk gain --daily                  # desglose por día
rtk discover                      # detecta oportunidades perdidas
rtk session                       # adopción de RTK por sesión
```

---

### Configuración

`%APPDATA%\rtk\config.toml` (Windows):

```toml
[tee]
enabled = true
mode = "failures"   # guarda output completo en fallos para que el LLM lo lea sin re-ejecutar
```

---

### Troubleshooting

**`rtk gain` dice "not a rtk command"** — tenés el binario equivocado (Rust Type Kit, no Token Killer):
```powershell
cargo uninstall rtk
cargo install --git https://github.com/rtk-ai/rtk
rtk gain    # debe mostrar el dashboard de ahorro
```

**Comando no filtrado** — usar `rtk proxy <cmd>` para trackearlo, o `rtk discover` para encontrar oportunidades perdidas.

**Debug**:
```bash
rtk git status -vvv
```

**Docs**: https://www.rtk-ai.app/guide

## CodeGraph — ahorro de tokens y contexto quirúrgico

CodeGraph indexa todos los símbolos del monorepo (Python + TypeScript) en SQLite
y permite consultarlos con una sola llamada en vez de leer archivos enteros.

**Regla de oro: antes de leer, consultá CodeGraph.** No abras archivos a ciegas.

### Cómo usar

- **Preguntá en lenguaje natural:** `codegraph_explore("flujo de evaluacion backend")`,
  `codegraph_explore("consultar_rfc_en_listas")`, `codegraph_explore("ingest_list")`
- **Nombrá símbolos o archivos:** `codegraph_explore("validar_estructura lookup.py")`
- **Para cambios, pedí el blast radius primero:** CodeGraph muestra qué funciones
  llaman a qué y qué tests cubren cada símbolo antes de editar.

### Lo que ahorra tokens (y qué NO hacer)

| En vez de esto (derrocha) | Hacé esto (ahorra) |
|---|---|
| Leer 4 archivos para entender un flujo | Un `codegraph_explore` con los nombres de los símbolos |
| Leer un archivo entero de 200 líneas para encontrar una función | `codegraph_explore("nombre_de_la_funcion")` — trae solo esa función y su contexto |
| Leer archivo por archivo para ver impacto de un cambio | `codegraph_explore("simbolo")` y leé el **blast radius** |
| Usar `grep` + múltiples `Read` para rastrear dependencias | CodeGraph ya indexó edges entre símbolos |
| Re-leer un archivo que CodeGraph ya devolvió en el mismo turno | CodeGraph devuelve source **verbatim** — ya lo leíste, no lo vuelvas a abrir |

### Por qué esto importa acá

Este repo tiene ~35 archivos entre `backend/` (Python) y `frontend/` (TypeScript).
Sin CodeGraph, cada tarea implica leer 4-10 archivos para entender contexto.
Con CodeGraph, una sola consulta reemplaza toda esa lectura. Es la diferencia
entre gastar 10-15K tokens en reads por tarea vs 2-3K.

### Importante

- CodeGraph está disponible como MCP tool (`codegraph_explore`).
- Usalo SIEMPRE antes de `Read`, `Grep` o `Glob` para entender código.
- CodeGraph ya devolvió el source de un archivo → tratalo como si ya lo
  hubieras leído. No lo abras de nuevo con `Read`.
- Si la consulta no encuentra lo que buscás, recién ahí caé a `Grep`/`Read`.

## Contexto persistente

Hay memoria guardada en Engram (proyecto `camtom-prueba-tecnica`) con todas las decisiones, correcciones y descubrimientos de la sesión de planificación completa — llamar `mem_context`/`mem_search` al iniciar para recuperarlo. No asumas nada sobre el "por qué" de una decisión que no esté en este archivo o en el plan; si no está documentado, está en esa memoria.

## Datos de prueba

3 expedientes sintéticos ya definidos en el plan (Fase 6): uno limpio con el RFC oficial de sandbox del SAT `EKU9003173C9`, uno con discrepancias mitigables (replica el ejemplo textual del brief), uno con un RFC real del listado 69-B Definitivos vigente. Los PDFs sintéticos deben generarse con texto seleccionable — nunca como imagen escaneada, Groq no hace OCR.
