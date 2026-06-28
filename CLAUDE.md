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

## Contexto persistente

Hay memoria guardada en Engram (proyecto `camtom-prueba-tecnica`) con todas las decisiones, correcciones y descubrimientos de la sesión de planificación completa — llamar `mem_context`/`mem_search` al iniciar para recuperarlo. No asumas nada sobre el "por qué" de una decisión que no esté en este archivo o en el plan; si no está documentado, está en esa memoria.

## Datos de prueba

3 expedientes sintéticos ya definidos en el plan (Fase 6): uno limpio con el RFC oficial de sandbox del SAT `EKU9003173C9`, uno con discrepancias mitigables (replica el ejemplo textual del brief), uno con un RFC real del listado 69-B Definitivos vigente. Los PDFs sintéticos deben generarse con texto seleccionable — nunca como imagen escaneada, Groq no hace OCR.
