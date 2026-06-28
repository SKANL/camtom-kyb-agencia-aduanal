# Borrador de correo — Entrega de prueba técnica

**Para:** Pedro Ríos (reclutador/ingeniero — Camtom)
**Asunto:** Prueba Técnica Software Engineer — Plataforma KYB Agente Aduanal — Gaspar Anguas

---

**Body:**

Buenas tardes, Pedro,

Adjunto la entrega de la prueba técnica para el puesto de Software Engineer en Camtom. A continuación los tres entregables solicitados, más algunas notas que me parecen relevantes y que no entraron en el README del repositorio.

## Entregables

### 1. Repositorio público — GitHub
[https://github.com/SKANL/camtom-kyb-agencia-aduanal](https://github.com/SKANL/camtom-kyb-agencia-aduanal)

El README.md contiene la documentación completa incluyendo arquitectura, rúbrica de scoring, instrucciones de uso local, decisiones técnicas documentadas, y el detalle del workflow con el que se construyó.

### 2. URLs del deploy — Vercel (producción)
- Frontend: https://frontend-khaki-eight-25.vercel.app
- Backend API: https://backend-nine-snowy-67.vercel.app (Health check: `/health`)

### 3. Transcript de la conversación con Claude Code
Incluido en `docs/conversation-transcript.md` dentro del repositorio.

---

## Lo que no está en el README (y creo que suma a la evaluación)

**Sobre el deadline de 48h:** El correo de la prueba llegó el viernes 26/06 a las 4:45pm. El domingo 28/06 a las 4:45pm entregué el último PR mergeado, con las 6 fases completas, 89 tests pasando, y ambos servicios desplegados en Vercel. Me pareció importante respetar el límite al minuto, no solo "antes del domingo".

**Sobre las decisiones de arquitectura que no se ven en el código:**

- **No hay autenticación ni autorización** — es una decisión consciente, no un descuido. En un demo público para evaluación, el auth friction solo entorpece la revisión. En producción usaría Supabase Auth + RLS (el schema ya está preparado para ello).

- **Supabase cloud-only, zero Docker** — Nunca usé el stack local de Supabase. Todas las migraciones se aplicaron directamente al proyecto cloud via `supabase db push` o el SQL Editor. Esto evita el version-skew entre entornos y es más representativo de cómo se trabaja en producción.

- **El frontend nunca toca Supabase directamente** — Toda lectura/escritura pasa por el backend REST. Esto no es solo "seguridad", es también *testabilidad*: el backend tiene 89 tests; si el frontend también accediera a Supabase directo, los tests tendrían que mockear dos superficies diferentes.

**Sobre el ETL de listas SAT (Fase 2):**

El brief pedía explícitamente datos reales del SAT, sin mocks. Esto presentó un problema real: el SAT no expone URLs estáticas para descargar los archivos XLSX del Art. 69 y 69-B; los genera dinámicamente mediante un formulario web. Esto significa que no hay una URL fija que el ETL pueda consumir automáticamente.

La solución fue documentar la limitación en código y en el README, diseñar los parsers contra la estructura esperada de los archivos (confirmada con ejemplos públicos disponibles), y dejar la ingest automática preparada para cuando el operador descargue manualmente los archivos. El pipeline de lookup SAT contra la tabla local está completo y testeado — el gap está solo en la descarga inicial, no en el consumo.

También descubrí que el artículo 49 Bis del CFF no tiene lista pública. Esa funcionalidad está documentada como *no implementada por falta de fuente pública*, no como un hueco en el desarrollo. Prefiero eso a inventar una fuente.

**Sobre el dígito verificador del RFC:**

Hubo un momento particularmente tenso: un subagente (revisor automático) reportó que el RFC sandbox oficial del SAT (`EKU9003173C9`) no cumplía el algoritmo módulo-11 y sugirió agregar una excepción hardcodeada. Verifiqué manualmente el cálculo y el RFC SÍ cumple el algoritmo. La excepción propuesta habría ocultado un bug real en la implementación. Esto refuerza por qué el "fresh-context review" (revisor sin memoria de la implementación) es más valioso que uno que arrastra contexto.

**Sobre la estructura del proyecto:**

Opté por un monorepo limpio: `frontend/` y `backend/`, raíz del repo solo con configs de tooling. Esto refleja cómo organizaría un proyecto real en Camtom — cada servicio es un proyecto Vercel independiente, desplegable por separado, sin dependencias circulares.

---

## Cronología real (48h)

| Bloque | Horas | Qué se hizo |
|---|---|---|
| Viernes 4:45pm – 8:00pm | 0–3h | Planificación: investigación con Gemini Deep Research, arquitectura, modelo de datos, rúbrica de scoring |
| Viernes 8:00pm – Sábado 1:00am | 3–8h | Fase 1: Scaffolding (Next.js + FastAPI + Supabase schema + deploy Vercel) |
| Sábado 1:00am – 10:00am | 8–17h | Fase 2: ETL SAT (RFC validator, parsers Art. 69/69-B, lookup + audit log, ingest pipeline) |
| Sábado 10:00am – 8:00pm | 17–27h | Fase 3: Motor de reglas determinístico (AI Harness + factores + score + lifecycle + evaluación) |
| Sábado 8:00pm – Domingo 2:00am | 27–33h | Fase 4: Extracción IA (schemas + Groq harness + OCR fallback + reconciliación semántica) |
| Domingo 2:00am – 12:00pm | 33–44h | Fase 5: Dashboard UI (tema Clickhouse, 9 páginas frontend, CRUD endpoints, score report) |
| Domingo 12:00pm – 4:45pm | 44–48h | Fase 6: Datos demo (PDFs sintéticos, 3 expedientes, README + documentación final) |

---

## Stack tecnológico completo

- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui (tema Clickhouse) + Zustand
- **Backend:** FastAPI (Python 3.13) + LangChain + langchain-groq + supabase-py
- **Databases:** Supabase Postgres + Supabase Storage
- **Deployment:** Vercel (dos proyectos independientes, Serverless Functions Python + Node)
- **AI Model:** Groq Llama 3 (extracción estructurada + reconciliación semántica)
- **Package management:** uv (Python) + pnpm (Node)
- **AI workflow:** Gentle AI (Spec-Driven Development con orchestrator + 12 sub-agentes especializados)
- **Code intelligence:** Codegraph (índice de símbolos pre-computado para consultas quirúrgicas)
- **Persistent memory:** Engram (63 observaciones preservadas entre 6+ sesiones de Claude Code)

Cualquier duda, estoy a disposición para ampliar técnicamente cualquiera de los puntos.

Saludos,
Gaspar Anguas
