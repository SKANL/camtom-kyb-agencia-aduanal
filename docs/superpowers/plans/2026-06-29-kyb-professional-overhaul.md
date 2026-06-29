# KYB Professional Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix scoring logic bugs, complete demo PDF scenarios, add SWR real-time updates, polish UX/CRUD flows, enrich KYB report with verifiable citations.

**Architecture:** Four independent blocks executed in dependency order — (A) backend correctness fixes first since they invalidate everything else; (B) SWR client-side cache layer replacing the Suspense/Server-Component polling pattern; (D) UX polish on top of the correct data layer; (C) report enrichment using already-fixed backend data. All backend changes are TDD-first. Frontend changes follow the existing shadcn/ui + Tailwind + Next.js App Router conventions.

**Tech Stack:** FastAPI + Python 3.13 + uv, Next.js 16 App Router + TypeScript + Tailwind + shadcn/ui, Supabase (cloud only), pnpm, SWR, Sonner

## Global Constraints

- Python: 3.13 pinned. Run all backend commands from `backend/` with `uv run`.
- Frontend: pnpm only. Never npm/yarn/npx inside `frontend/`.
- No `supabase start` / Docker local stack — Supabase cloud only.
- No Co-Authored-By in commits. Conventional commits only.
- TDD strict for backend: write failing test → see it fail → implement → see it pass → commit.
- No placeholders, no TODOs, no "similar to Task N" shortcuts.
- CodeGraph is available: query with `mcp__codegraph__codegraph_explore` before reading files.
- RTK: prefix all Bash commands with `rtk` (e.g. `rtk git status`, `rtk test "uv run pytest ..."`).
- Engram: save every significant decision/bug fix via `mem_save` before completing each task.

---

## File Map

```
BLOCK A — Backend fixes
  backend/src/domain/scoring/engine.py            MODIFY (fix rfc_formato_invalido special case)
  backend/src/tests/test_scoring_engine.py        MODIFY (add 2 new edge-case tests)
  backend/src/tests/test_scoring_factors_sat.py   MODIFY (add combined-factor test)
  backend/scripts/generate_demo_pdfs.py           MODIFY (add 4 missing doc type generators + all 3 scenarios updated)
  backend/scripts/seed_demo_data.py               CREATE (direct Supabase seeding, bypasses AI extraction)

BLOCK B — Frontend real-time
  frontend/hooks/use-expedientes.ts               CREATE (useSWR hook + global key)
  frontend/components/providers.tsx               CREATE (SWRConfig provider)
  frontend/app/layout.tsx                         MODIFY (add SWRConfig provider + Toaster)
  frontend/app/page.tsx                           MODIFY (convert ExpedientesContent to Client Component using SWR)
  frontend/components/ExpedienteActions.tsx       MODIFY (replace router.refresh() with global mutate())
  frontend/app/expedientes/nuevo/page.tsx         MODIFY (add toast + mutate() after create)
  frontend/app/expedientes/[id]/reporte/EvaluateButton.tsx  MODIFY (add toast + mutate() after evaluate)

BLOCK D — UX/CRUD polish
  frontend/components/header.tsx                  MODIFY (remove Admin SAT from nav)
  frontend/app/expedientes/[id]/reporte/page.tsx  MODIFY (add re-evaluate banner when status=needs_update)
  frontend/app/expedientes/[id]/page.tsx          READ (confirm upload flow is complete, fix if not)

BLOCK C — Enriched report
  backend/src/api/routers/expedientes.py          MODIFY (add GET /expedientes/{id}/evaluations list endpoint)
  frontend/lib/api-client.ts                      MODIFY (add listEvaluations() + types)
  frontend/components/EvaluationHistory.tsx       CREATE (evaluation history accordion)
  frontend/components/ComplianceContext.tsx       CREATE (RGCE 1.4.14 compliance panel)
  frontend/app/expedientes/[id]/reporte/page.tsx  MODIFY (add EvaluationHistory + ComplianceContext sections)
```

---

## BLOCK A — Backend Correctness (TDD first)

### Task 1: Fix scoring engine + TDD tests

**Files:**
- Modify: `backend/src/domain/scoring/engine.py`
- Modify: `backend/src/tests/test_scoring_engine.py`

**The bug:** When `rfc_formato_invalido` is present AND accumulated score ≥ 70 (from discrepancias + completitud factors), the special-case check on line 19 of `engine.py` forces `decision = "review_required"` — overriding the score-based threshold. An RFC with format error + 3 missing docs accumulates 60+45 = 105 pts but is classified as `review_required` instead of `high_risk`.

**Fix:** Remove the `rfc_formato_invalido` special case. The factor already carries 60 pts which places it in `review_required` territory on its own (30 ≤ 60 < 70). Combined with other factors it correctly escalates. The existing test `test_rfc_invalido_fuerza_piso_review_required` still passes since 60 < 70.

- [ ] **Step 1.1: Write two failing tests**

```python
# backend/src/tests/test_scoring_engine.py — ADD these two tests at the end of the file:

def test_rfc_invalido_mas_alta_penalizacion_es_high_risk():
    """RFC inválido (60 pts) + docs faltantes (45 pts) = 105 pts → high_risk.
    
    Antes del fix, el special-case forzaba review_required incluso con 105 pts.
    """
    from domain.scoring.factors import Factor
    factores = [
        Factor("rfc_formato_invalido", 60, False, "x"),
        Factor("doc_missing", 15, False, "falta acta"),
        Factor("doc_missing", 15, False, "falta poder"),
        Factor("doc_missing", 15, False, "falta encargo"),
    ]
    r = evaluar(factores)
    assert r.score_total == 105
    assert r.decision == "high_risk"


def test_rfc_invalido_solo_sigue_siendo_review_required():
    """Solo RFC inválido = 60 pts → review_required (30 ≤ 60 < 70).
    
    Confirma que el fix no rompe el comportamiento para el caso base.
    """
    from domain.scoring.factors import Factor
    r = evaluar([Factor("rfc_formato_invalido", 60, False, "x")])
    assert r.score_total == 60
    assert r.decision == "review_required"
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
cd backend && rtk test "uv run pytest src/tests/test_scoring_engine.py -v"
```

Expected: `test_rfc_invalido_mas_alta_penalizacion_es_high_risk` FAILS with `AssertionError: assert 'review_required' == 'high_risk'`. The second test may already pass.

- [ ] **Step 1.3: Fix engine.py — remove the special-case check**

Full replacement of `backend/src/domain/scoring/engine.py`:

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
    elif score_total >= UMBRAL_HIGH_RISK:
        decision = "high_risk"
    elif score_total >= UMBRAL_REVIEW_REQUIRED:
        decision = "review_required"
    else:
        decision = "safe"
    return ResultadoEvaluacion(score_total, decision, critical_blocks, factores)
```

- [ ] **Step 1.4: Run all scoring tests to confirm they pass**

```bash
cd backend && rtk test "uv run pytest src/tests/test_scoring_engine.py src/tests/test_scoring_factors_sat.py src/tests/test_scoring_factors_completitud.py -v"
```

Expected: ALL PASS. All 4 tests in `test_scoring_engine.py` should pass (the two original + two new).

- [ ] **Step 1.5: Run full test suite to confirm no regressions**

```bash
cd backend && rtk test "uv run pytest src/tests/ -v"
```

Expected: All tests pass.

- [ ] **Step 1.6: Commit**

```bash
rtk git add backend/src/domain/scoring/engine.py backend/src/tests/test_scoring_engine.py
rtk git commit -m "fix(scoring): remove rfc_formato_invalido special case — score thresholds now apply correctly at 70+ pts"
```

---

### Task 2: Complete demo PDFs — add 4 missing document types

**Files:**
- Modify: `backend/scripts/generate_demo_pdfs.py`

**The problem:** `DOCUMENTOS_ESPERADOS` in `factors.py` has 8 types: `acta_constitutiva`, `identificacion_rep_legal`, `poder_notarial`, `encargo_conferido`, `comprobante_domicilio`, `rfc`, `csf`, `manifestacion_protesta`. Current script only generates 4: `acta_constitutiva`, `comprobante_domicilio`, `csf`, `manifestacion_protesta`. Missing 4 types cause 4 × 15 = 60 pts of `doc_missing` in every scenario — making the "clean" scenario score 60 pts (review_required) instead of 0 (safe).

**Important note:** PDFs alone don't affect scoring. Scoring reads from the `documentos` DB table. The PDFs are for the UPLOAD demo flow. For direct demo scoring, use the `seed_demo_data.py` script in Task 3. This task makes the PDFs complete so the upload-then-extract-then-evaluate flow works end-to-end.

- [ ] **Step 2.1: Replace `generate_demo_pdfs.py` with complete version (all 8 doc types)**

Full replacement of `backend/scripts/generate_demo_pdfs.py`:

```python
"""
Demo PDF generator for KYB platform.

Generates text-selectable PDFs for all 8 required document types across 3 scenarios:
  escenario_1_limpio   — EKU9003173C9, all docs match, clean → safe
  escenario_2_discrepancia — COX010101AB1, intentional mismatches → review_required
  escenario_3_alto_riesgo  — AAA120730823, in 69-B definitivos list → high_risk

Run: cd backend && uv run python scripts/generate_demo_pdfs.py
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path(__file__).parent / "demo_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)


def _footer(c, w):
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 1.5 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")


def make_csf(path: Path, rfc: str, razon_social: str, domicilio: str, rep_legal: str, fecha: str = "2026-06-01"):
    """Constancia de Situación Fiscal."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 2 * cm, "CONSTANCIA DE SITUACIÓN FISCAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Servicio de Administración Tributaria")
    c.line(2 * cm, h - 3.2 * cm, w - 2 * cm, h - 3.2 * cm)
    fields = [
        ("RFC:", rfc),
        ("Razón Social:", razon_social),
        ("Régimen Fiscal:", "601 - General de Ley Personas Morales"),
        ("Domicilio Fiscal:", domicilio),
        ("Representante Legal:", rep_legal),
        ("Fecha de emisión:", fecha),
        ("Estatus en el RFC:", "ACTIVO"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(7 * cm, y, value)
        y -= 0.8 * cm
    _footer(c, w)
    c.save()


def make_acta(path: Path, rfc: str, razon_social: str, rep_legal: str, socios: list[str]):
    """Acta Constitutiva."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "ACTA CONSTITUTIVA")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 2.7 * cm, "Sociedad Anónima de Capital Variable")
    y = h - 4 * cm
    lines = [
        "En la Ciudad de México, siendo las 10:00 horas del 1 de enero de 2015, comparecen:",
        f"Razón Social: {razon_social}",
        f"RFC: {rfc}",
        f"Representante Legal: {rep_legal}",
        "",
        "SOCIOS / ACCIONISTAS:",
    ]
    c.setFont("Helvetica", 9)
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.65 * cm
    for socio in socios:
        c.drawString(2.5 * cm, y, f"• {socio}")
        y -= 0.65 * cm
    _footer(c, w)
    c.save()


def make_comprobante_domicilio(path: Path, razon_social: str, domicilio: str, fecha: str):
    """Comprobante de Domicilio (recibo CFE)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "COMPROBANTE DE DOMICILIO")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "CFE — Compañía de Luz y Fuerza del Centro")
    fields = [
        ("Nombre / Razón Social:", razon_social),
        ("Domicilio:", domicilio),
        ("Fecha de emisión:", fecha),
        ("Periodo de servicio:", "Mayo 2026"),
        ("No. de cuenta:", "00123456789"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(8 * cm, y, value)
        y -= 0.8 * cm
    _footer(c, w)
    c.save()


def make_manifestacion(path: Path, razon_social: str, rfc: str, rep_legal: str, declara: bool):
    """Manifestación bajo Protesta de Decir Verdad."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 2 * cm, "MANIFESTACIÓN BAJO PROTESTA DE DECIR VERDAD")
    c.setFont("Helvetica", 9)
    y = h - 3.5 * cm
    texto = (
        f"Yo, {rep_legal}, en mi carácter de representante legal de {razon_social} "
        f"(RFC: {rfc}), manifiesto bajo protesta de decir verdad que la empresa que represento:"
    )
    words = texto.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, "Helvetica", 9) < (w - 4 * cm):
            line = test
        else:
            c.drawString(2 * cm, y, line)
            y -= 0.55 * cm
            line = word
    if line:
        c.drawString(2 * cm, y, line)
        y -= 0.8 * cm

    if declara:
        clausulas = [
            "1. No se encuentra en los supuestos del Art. 69-B del CFF (EFOS).",
            "2. No ha transmitido indebidamente pérdidas fiscales (Art. 69-B Bis CFF).",
            "3. No realiza operaciones de contrabando técnico (Art. 49 Bis CFF).",
            "4. Toda la información proporcionada es verídica y verificable.",
        ]
    else:
        clausulas = [
            "1. La empresa cumple con sus obligaciones fiscales generales.",
            "2. Toda la información proporcionada es verídica.",
        ]
    for clausula in clausulas:
        c.drawString(2 * cm, y, clausula)
        y -= 0.65 * cm
    y -= 0.5 * cm
    c.drawString(2 * cm, y, "Firma: ________________________    Fecha: 2026-06-15")
    _footer(c, w)
    c.save()


def make_identificacion_rep_legal(path: Path, nombre_completo: str, fecha_vencimiento: str = "2029-12-31"):
    """Identificación oficial del representante legal (INE/pasaporte simplificado)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "IDENTIFICACIÓN OFICIAL DEL REPRESENTANTE LEGAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Instituto Nacional Electoral — Credencial para Votar")
    fields = [
        ("Nombre Completo:", nombre_completo),
        ("Tipo de ID:", "Credencial para Votar (INE)"),
        ("Clave de Elector:", "PEGJN85010100H800"),
        ("Fecha de Vencimiento:", fecha_vencimiento),
        ("CURP:", "PEGJ850101HDFRZN09"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(8 * cm, y, value)
        y -= 0.8 * cm
    _footer(c, w)
    c.save()


def make_poder_notarial(path: Path, nombre_representante: str, razon_social: str, alcance: str = "Actos de Administración y Dominio"):
    """Poder Notarial."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "PODER NOTARIAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Protocolo 1234 — Notaría Pública No. 45, Ciudad de México")
    c.setFont("Helvetica", 9)
    y = h - 4 * cm
    lines = [
        f"Por medio del presente instrumento, {razon_social} otorga poder notarial amplio a:",
        f"Nombre del Representante: {nombre_representante}",
        f"Alcance del Poder: {alcance}",
        "",
        "El presente poder incluye facultades para representar a la empresa ante:",
        "  • Autoridades fiscales (SAT, SHCP)",
        "  • Aduanas y agentes aduanales",
        "  • Instituciones financieras",
        "",
        "Fecha de firma: 2020-01-15",
        "Notario Público: Lic. Roberto Martínez Vega",
        "Número de escritura: 45,678",
    ]
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.65 * cm
    _footer(c, w)
    c.save()


def make_encargo_conferido(path: Path, rfc_agente_aduanal: str, razon_social: str, alcance: str = "Importación y Exportación de mercancías en general", fecha_vigencia: str = "2027-12-31"):
    """Encargo Conferido al Agente Aduanal."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 2 * cm, "ENCARGO CONFERIDO AL AGENTE ADUANAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Conforme al Art. 59 fracción III de la Ley Aduanera")
    fields = [
        ("RFC Agente Aduanal:", rfc_agente_aduanal),
        ("Empresa cliente:", razon_social),
        ("Alcance:", alcance),
        ("Fecha de vigencia:", fecha_vigencia),
        ("Tipo de operaciones:", "A/E — Importación y Exportación"),
        ("Aduana(s) designada(s):", "México, Veracruz, Laredo"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(8 * cm, y, value)
        y -= 0.8 * cm
    y -= 0.5 * cm
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Firma del representante legal: ________________________    Fecha: 2024-01-10")
    _footer(c, w)
    c.save()


def make_comprobante_rfc(path: Path, rfc: str, razon_social: str):
    """Comprobante de RFC (cédula de identificación fiscal)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "CÉDULA DE IDENTIFICACIÓN FISCAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Servicio de Administración Tributaria")
    fields = [
        ("RFC:", rfc),
        ("Nombre / Razón Social:", razon_social),
        ("Tipo de persona:", "Moral"),
        ("Fecha de alta en RFC:", "2015-01-15"),
        ("Régimen:", "601 - General de Ley Personas Morales"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(8 * cm, y, value)
        y -= 0.8 * cm
    _footer(c, w)
    c.save()


def generate():
    # ── Scenario 1: CLEAN — EKU9003173C9 ──────────────────────────────────────
    # All 8 docs. Data matches across docs. RFC clean in SAT lists.
    # Expected scoring: 0 pts → safe
    clean_dir = OUTPUT_DIR / "escenario_1_limpio"
    clean_dir.mkdir(exist_ok=True)
    make_csf(clean_dir / "csf.pdf", "EKU9003173C9", "Escuela Kemper Urgate SA de CV",
             "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700", "Juan Pérez García")
    make_acta(clean_dir / "acta_constitutiva.pdf", "EKU9003173C9", "Escuela Kemper Urgate SA de CV",
              "Juan Pérez García", ["Juan Pérez García (60%)", "María López Ramírez (40%)"])
    make_comprobante_domicilio(clean_dir / "comprobante_domicilio.pdf", "Escuela Kemper Urgate SA de CV",
                               "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700", "2026-06-01")
    make_manifestacion(clean_dir / "manifestacion_protesta.pdf", "Escuela Kemper Urgate SA de CV",
                       "EKU9003173C9", "Juan Pérez García", declara=True)
    make_identificacion_rep_legal(clean_dir / "identificacion_rep_legal.pdf", "Juan Pérez García")
    make_poder_notarial(clean_dir / "poder_notarial.pdf", "Juan Pérez García", "Escuela Kemper Urgate SA de CV")
    make_encargo_conferido(clean_dir / "encargo_conferido.pdf", "CAMT930401AB9",
                           "Escuela Kemper Urgate SA de CV")
    make_comprobante_rfc(clean_dir / "rfc.pdf", "EKU9003173C9", "Escuela Kemper Urgate SA de CV")

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    # All 8 docs. Intentional mismatches in razon_social + representante.
    # Expected scoring: disc_razon_social (30) + disc_representante (25) = 55 pts → review_required
    disc_dir = OUTPUT_DIR / "escenario_2_discrepancia"
    disc_dir.mkdir(exist_ok=True)
    make_csf(disc_dir / "csf.pdf", "COX010101AB1", "Corporativo X SA de CV",
             "Avenida Insurgentes Sur Num 123, Colonia Roma", "María López")
    make_acta(disc_dir / "acta_constitutiva.pdf", "COX010101AB1", "Corporativo X, S.A. de C.V.",
              "Maria Lopez Hernandez", ["María López Hernandez (51%)", "Roberto Sánchez Cruz (49%)"])
    make_comprobante_domicilio(disc_dir / "comprobante_domicilio.pdf", "Corporativo X SA de CV",
                               "Insurgentes Sur 123, Roma", "2026-06-01")
    make_manifestacion(disc_dir / "manifestacion_protesta.pdf", "Corporativo X SA de CV",
                       "COX010101AB1", "María López", declara=True)
    make_identificacion_rep_legal(disc_dir / "identificacion_rep_legal.pdf", "Maria Lopez Hernandez")
    make_poder_notarial(disc_dir / "poder_notarial.pdf", "Maria Lopez Hernandez",
                        "Corporativo X SA de CV")
    make_encargo_conferido(disc_dir / "encargo_conferido.pdf", "CAMT930401AB9", "Corporativo X SA de CV")
    make_comprobante_rfc(disc_dir / "rfc.pdf", "COX010101AB1", "Corporativo X SA de CV")

    # ── Scenario 3: HIGH RISK — AAA120730823 ───────────────────────────────────
    # All 8 docs. RFC in Art. 69-B definitivos list → critical block → high_risk.
    # Manifestacion missing clauses (intentional) → manifestacion_incompleta (+20 pts).
    risk_dir = OUTPUT_DIR / "escenario_3_alto_riesgo"
    risk_dir.mkdir(exist_ok=True)
    make_csf(risk_dir / "csf.pdf", "AAA120730823", "Empresa en Lista Negra SA de CV",
             "Calle Reforma 456, Col. Centro, CDMX, CP 06000", "Carlos Sánchez")
    make_acta(risk_dir / "acta_constitutiva.pdf", "AAA120730823", "Empresa en Lista Negra SA de CV",
              "Carlos Sánchez", ["Carlos Sánchez (100%)"])
    make_comprobante_domicilio(risk_dir / "comprobante_domicilio.pdf", "Empresa en Lista Negra SA de CV",
                               "Calle Reforma 456, Col. Centro, CDMX, CP 06000", "2026-06-01")
    make_manifestacion(risk_dir / "manifestacion_protesta.pdf", "Empresa en Lista Negra SA de CV",
                       "AAA120730823", "Carlos Sánchez", declara=False)
    make_identificacion_rep_legal(risk_dir / "identificacion_rep_legal.pdf", "Carlos Sánchez")
    make_poder_notarial(risk_dir / "poder_notarial.pdf", "Carlos Sánchez", "Empresa en Lista Negra SA de CV")
    make_encargo_conferido(risk_dir / "encargo_conferido.pdf", "CAMT930401AB9",
                           "Empresa en Lista Negra SA de CV")
    make_comprobante_rfc(risk_dir / "rfc.pdf", "AAA120730823", "Empresa en Lista Negra SA de CV")

    print("Demo PDFs generated:")
    for f in sorted(OUTPUT_DIR.rglob("*.pdf")):
        print(f"  {f.relative_to(OUTPUT_DIR.parent.parent)}")


if __name__ == "__main__":
    generate()
```

- [ ] **Step 2.2: Regenerate demo PDFs**

```bash
cd backend && uv run python scripts/generate_demo_pdfs.py
```

Expected output: 24 PDFs listed (8 per scenario × 3 scenarios).

- [ ] **Step 2.3: Verify output**

```bash
ls backend/scripts/demo_pdfs/escenario_1_limpio/
```

Expected: 8 files — `acta_constitutiva.pdf comprobante_domicilio.pdf csf.pdf encargo_conferido.pdf identificacion_rep_legal.pdf manifestacion_protesta.pdf poder_notarial.pdf rfc.pdf`

- [ ] **Step 2.4: Commit**

```bash
rtk git add backend/scripts/generate_demo_pdfs.py backend/scripts/demo_pdfs/
rtk git commit -m "feat(demo): add 4 missing doc types to demo PDFs — all 3 scenarios now have complete 8-document sets"
```

---

### Task 3: Demo data seeding script (direct Supabase, bypasses AI)

**Files:**
- Create: `backend/scripts/seed_demo_data.py`

**Why:** Even with correct PDFs, the upload → extract → review flow requires Groq AI. For a reliable demo, seed Supabase directly with pre-computed fields and `extraction_status = "human_reviewed"`. Run evaluate at the end to produce real scores.

**Prerequisites:** `backend/.env` must have `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

- [ ] **Step 3.1: Create seed script**

Create `backend/scripts/seed_demo_data.py`:

```python
"""
Seed demo data directly into Supabase for the KYB platform demo.

Creates 3 complete expedientes with all documents, fields, socios, and runs
evaluation. Uses pre-computed fields (extraction_status=human_reviewed) to
bypass the AI extraction step — results are deterministic.

Usage:
  cd backend
  uv run python scripts/seed_demo_data.py

Optional: clear existing demo data first with --clean flag:
  uv run python scripts/seed_demo_data.py --clean
"""

import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

TODAY = date.today().isoformat()
NOW = datetime.now(timezone.utc).isoformat()

DEMO_TAG = "demo_seed_v1"


def make_id() -> str:
    return str(uuid.uuid4())


def seed(supabase):
    # ── Scenario 1: CLEAN — EKU9003173C9 ──────────────────────────────────────
    exp1_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp1_id,
        "razon_social": "Escuela Kemper Urgate SA de CV",
        "rfc": "EKU9003173C9",
        "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        "representante_legal": "Juan Pérez García",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs1 = [
        {"doc_type": "csf", "fields": {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
            "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
            "socios": [{"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDF", "porcentaje": 60},
                       {"nombre": "María López Ramírez", "rfc": "LORM900215MDF", "porcentaje": 40}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Juan Pérez García", "fecha_vencimiento": "2029-12-31",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Juan Pérez García", "alcance": "Actos de Administración y Dominio",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación de mercancías en general",
            "fecha_vigencia": "2027-12-31",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs1:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp1_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp1_id, "nombre": "Juan Pérez García",
         "rfc": "PEGJ850101HDF", "porcentaje": 60},
        {"id": make_id(), "expediente_id": exp1_id, "nombre": "María López Ramírez",
         "rfc": "LORM900215MDF", "porcentaje": 40},
    ]).execute()

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    exp2_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp2_id,
        "razon_social": "Corporativo X SA de CV",
        "rfc": "COX010101AB1",
        "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma",
        "representante_legal": "María López",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs2 = [
        {"doc_type": "csf", "fields": {
            "rfc": "COX010101AB1", "razon_social": "Corporativo X SA de CV",
            "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "COX010101AB1",
            "razon_social": "Corporativo X, S.A. de C.V.",
            "socios": [{"nombre": "María López Hernandez", "rfc": "LOHM750310MDF", "porcentaje": 51},
                       {"nombre": "Roberto Sánchez Cruz", "rfc": "SACR800520HDF", "porcentaje": 49}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Insurgentes Sur 123, Roma",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Maria Lopez Hernandez", "fecha_vencimiento": "2028-06-30",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Maria Lopez Hernandez",
            "alcance": "Actos de Administración",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación de mercancías en general",
            "fecha_vigencia": "2027-06-30",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs2:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp2_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp2_id, "nombre": "María López Hernandez",
         "rfc": "LOHM750310MDF", "porcentaje": 51},
        {"id": make_id(), "expediente_id": exp2_id, "nombre": "Roberto Sánchez Cruz",
         "rfc": "SACR800520HDF", "porcentaje": 49},
    ]).execute()

    # ── Scenario 3: HIGH RISK — AAA120730823 ───────────────────────────────────
    exp3_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp3_id,
        "razon_social": "Empresa en Lista Negra SA de CV",
        "rfc": "AAA120730823",
        "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        "representante_legal": "Carlos Sánchez",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs3 = [
        {"doc_type": "csf", "fields": {
            "rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
            "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
            "socios": [{"nombre": "Carlos Sánchez", "rfc": "SACC800401HDF", "porcentaje": 100}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": False}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Carlos Sánchez", "fecha_vencimiento": "2027-09-15",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Carlos Sánchez", "alcance": "Actos de Administración y Dominio",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación",
            "fecha_vigencia": "2027-01-31",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs3:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp3_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp3_id, "nombre": "Carlos Sánchez",
         "rfc": "SACC800401HDF", "porcentaje": 100},
    ]).execute()

    return exp1_id, exp2_id, exp3_id


def clean_demo_data(supabase):
    """Delete expedientes with the demo RFC values."""
    demo_rfcs = ["EKU9003173C9", "COX010101AB1", "AAA120730823"]
    for rfc in demo_rfcs:
        rows = supabase.table("expedientes").select("id").eq("rfc", rfc).execute().data
        for row in rows:
            exp_id = row["id"]
            supabase.table("documentos").delete().eq("expediente_id", exp_id).execute()
            supabase.table("socios").delete().eq("expediente_id", exp_id).execute()
            supabase.table("evaluations").delete().eq("expediente_id", exp_id).execute()
            supabase.table("consultas_sat").delete().eq("expediente_id", exp_id).execute()
            supabase.table("expedientes").delete().eq("id", exp_id).execute()
    print("Demo data cleaned.")


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    if "--clean" in sys.argv:
        clean_demo_data(supabase)
        return

    print("Seeding demo expedientes...")
    exp1_id, exp2_id, exp3_id = seed(supabase)

    # Run evaluations via the service layer
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from services.evaluation_service import evaluar_expediente
    from services.reconciliation_service import reconciliar_expediente

    for exp_id, name in [(exp1_id, "Escenario 1 — Limpio"), (exp2_id, "Escenario 2 — Discrepancia"), (exp3_id, "Escenario 3 — Alto Riesgo")]:
        try:
            recon = reconciliar_expediente(supabase, exp_id)
            result = evaluar_expediente(supabase, exp_id, recon)
            print(f"  {name}: score={result['score_total']} decision={result['decision']}")
        except Exception as e:
            print(f"  {name}: evaluation failed — {e}")

    print("\nDone. Open the frontend to see the seeded expedientes.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3.2: Install python-dotenv if not present**

```bash
cd backend && uv add python-dotenv
```

- [ ] **Step 3.3: Commit**

```bash
rtk git add backend/scripts/seed_demo_data.py backend/pyproject.toml backend/uv.lock
rtk git commit -m "feat(demo): add seed_demo_data.py script for deterministic demo without AI extraction"
```

---

## BLOCK B — Frontend Real-time (SWR)

### Task 4: Install SWR + create expedientes hook

**Files:**
- Create: `frontend/hooks/use-expedientes.ts`
- Create: `frontend/components/providers.tsx`

- [ ] **Step 4.1: Install SWR**

```bash
cd frontend && pnpm add swr
```

- [ ] **Step 4.2: Create SWR hook**

Create `frontend/hooks/use-expedientes.ts`:

```typescript
import useSWR, { mutate } from "swr";
import { api, type Expediente } from "@/lib/api-client";

export const EXPEDIENTES_KEY = "/expedientes";

const fetcher = () => api.listExpedientes();

export function useExpedientes(fallbackData?: Expediente[]) {
  return useSWR(EXPEDIENTES_KEY, fetcher, {
    fallbackData,
    revalidateOnFocus: true,
    dedupingInterval: 2000,
  });
}

export function revalidateExpedientes() {
  return mutate(EXPEDIENTES_KEY);
}
```

- [ ] **Step 4.3: Create SWRConfig provider**

Create `frontend/components/providers.tsx`:

```tsx
"use client";
import { SWRConfig } from "swr";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: true,
        shouldRetryOnError: false,
      }}
    >
      {children}
    </SWRConfig>
  );
}
```

- [ ] **Step 4.4: Commit**

```bash
rtk git add frontend/hooks/use-expedientes.ts frontend/components/providers.tsx frontend/package.json frontend/pnpm-lock.yaml
rtk git commit -m "feat(frontend): add SWR + useExpedientes hook for real-time data"
```

---

### Task 5: Convert dashboard to real-time Client Component

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/components/ExpedienteActions.tsx`
- Modify: `frontend/app/expedientes/[id]/reporte/EvaluateButton.tsx`

- [ ] **Step 5.1: Add Providers to layout**

Modify `frontend/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "Camtom KYB",
  description: "Plataforma KYB para agencia aduanal — Regla 1.4.14 RGCE 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>
          <Header />
          <div className="flex-1">{children}</div>
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 5.2: Convert dashboard page to hybrid Server+Client**

Full replacement of `frontend/app/page.tsx`:

```tsx
import { api, type Expediente, type Decision } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { ExpedienteActions } from "@/components/ExpedienteActions";
import { ExpedientesList } from "@/components/ExpedientesList";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let initialExpedientes: Expediente[] = [];
  try {
    initialExpedientes = await api.listExpedientes();
  } catch {
    // Backend unreachable at build time
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Expedientes KYB</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Evaluación de riesgo — Regla 1.4.14 RGCE 2026
          </p>
        </div>
        <Link
          href="/expedientes/nuevo"
          className="inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
        >
          + Nuevo expediente
        </Link>
      </div>
      <ExpedientesList initialExpedientes={initialExpedientes} />
    </main>
  );
}
```

- [ ] **Step 5.3: Create ExpedientesList client component**

Create `frontend/components/ExpedientesList.tsx`:

```tsx
"use client";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ExpedienteActions } from "@/components/ExpedienteActions";
import { useExpedientes } from "@/hooks/use-expedientes";
import type { Expediente, Decision } from "@/lib/api-client";

const DECISION_BADGE: Record<Decision, { label: string; className: string }> = {
  safe: { label: "Aprobado", className: "bg-success/15 text-success border-success/20" },
  review_required: { label: "Revisión requerida", className: "bg-warning/15 text-warning border-warning/20" },
  high_risk: { label: "Alto riesgo", className: "bg-destructive/15 text-destructive border-destructive/20" },
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  completed: "Completado",
  needs_update: "Actualización requerida",
  in_progress: "En progreso",
};

export function ExpedientesList({ initialExpedientes }: { initialExpedientes: Expediente[] }) {
  const { data: expedientes = initialExpedientes, isLoading } = useExpedientes(initialExpedientes);

  const safe = expedientes.filter((e) => e.decision === "safe").length;
  const flagged = expedientes.filter(
    (e) => e.decision === "review_required" || e.decision === "high_risk"
  ).length;
  const pending = expedientes.filter((e) => !e.decision).length;

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Total expedientes</p>
          <p className="text-3xl font-bold">{expedientes.length}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Aprobados</p>
          <p className="text-3xl font-bold text-success">{safe}</p>
          <p className="text-xs text-muted-foreground mt-1">safe ✓</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Requieren atención</p>
          <p className="text-3xl font-bold text-warning">{flagged + pending}</p>
          {pending > 0 && <p className="text-xs text-muted-foreground mt-1">{pending} sin evaluar</p>}
        </div>
      </div>

      {isLoading && expedientes.length === 0 ? (
        <div className="grid gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-card animate-pulse" />
          ))}
        </div>
      ) : expedientes.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg font-medium mb-2">Sin expedientes registrados</p>
          <p className="text-sm">Crea el primero para comenzar el proceso KYB.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-card">
              <tr>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">RFC</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Estado</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Decisión</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Score</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {expedientes.map((e) => {
                const badge = e.decision ? DECISION_BADGE[e.decision] : null;
                const statusLabel = STATUS_LABEL[e.status] ?? e.status;
                return (
                  <tr
                    key={e.id}
                    className="border-t border-border hover:bg-card/60 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium">
                      <Link
                        href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
                        className="hover:text-primary transition-colors"
                      >
                        {e.razon_social}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground text-xs">{e.rfc}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{statusLabel}</td>
                    <td className="px-4 py-3">
                      {badge ? (
                        <Badge className={badge.className}>{badge.label}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">Sin evaluar</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm">
                      <div className="flex items-center justify-end gap-3">
                        {e.score_total !== null ? (
                          <span className="text-primary font-bold">{e.score_total} pts</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                        <Link
                          href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
                          className="text-muted-foreground hover:text-primary transition-colors"
                          title={e.decision ? "Ver reporte" : "Cargar documentos"}
                        >
                          <ChevronRight className="size-4" />
                        </Link>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ExpedienteActions expediente={e} redirectOnDelete={false} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 5.4: Update ExpedienteActions to use global SWR mutate**

Full replacement of `frontend/components/ExpedienteActions.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Expediente } from "@/lib/api-client";
import { revalidateExpedientes } from "@/hooks/use-expedientes";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

type Props = {
  expediente: Pick<
    Expediente,
    "id" | "razon_social" | "rfc" | "domicilio_fiscal" | "representante_legal"
  >;
  redirectOnDelete?: boolean;
};

export function ExpedienteActions({ expediente, redirectOnDelete = false }: Props) {
  const router = useRouter();

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editFields, setEditFields] = useState({
    razon_social: expediente.razon_social ?? "",
    rfc: expediente.rfc ?? "",
    domicilio_fiscal: expediente.domicilio_fiscal ?? "",
    representante_legal: expediente.representante_legal ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEdit() {
    setSaving(true);
    setError(null);
    try {
      await api.updateExpediente(expediente.id, {
        razon_social: editFields.razon_social || undefined,
        rfc: editFields.rfc || undefined,
        domicilio_fiscal: editFields.domicilio_fiscal || undefined,
        representante_legal: editFields.representante_legal || undefined,
      });
      setEditOpen(false);
      await revalidateExpedientes();
      toast.success("Expediente actualizado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
      toast.error("No se pudo guardar el expediente");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await api.deleteExpediente(expediente.id);
      setDeleteOpen(false);
      await revalidateExpedientes();
      toast.success(`Expediente "${expediente.razon_social}" eliminado`);
      if (redirectOnDelete) {
        router.push("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
      toast.error("No se pudo eliminar el expediente");
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => { setError(null); setEditOpen(true); }}
          aria-label="Editar expediente"
        >
          <Pencil className="size-3.5" />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => { setError(null); setDeleteOpen(true); }}
          aria-label="Eliminar expediente"
          className="text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar expediente</DialogTitle>
            <DialogDescription>
              Modificá los datos del expediente. El RFC se normaliza a mayúsculas.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-1">
            {(
              [
                { key: "razon_social", label: "Razón social" },
                { key: "rfc", label: "RFC" },
                { key: "domicilio_fiscal", label: "Domicilio fiscal" },
                { key: "representante_legal", label: "Representante legal" },
              ] as const
            ).map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground block mb-1">{label}</label>
                <input
                  value={editFields[key]}
                  onChange={(e) => setEditFields({ ...editFields, [key]: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            ))}
            {error && <p className="text-destructive text-xs">{error}</p>}
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />} disabled={saving}>
              Cancelar
            </DialogClose>
            <Button onClick={handleEdit} disabled={saving}>
              {saving ? "Guardando…" : "Guardar cambios"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar expediente</DialogTitle>
            <DialogDescription>
              Esta acción es irreversible. Se eliminará el expediente{" "}
              <strong>{expediente.razon_social}</strong> junto con todos sus documentos,
              evaluaciones y registros de auditoría.
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-destructive text-xs px-1">{error}</p>}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />} disabled={deleting}>
              Cancelar
            </DialogClose>
            <Button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/80"
            >
              {deleting ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 5.5: Update EvaluateButton to use SWR mutate + toast**

Full replacement of `frontend/app/expedientes/[id]/reporte/EvaluateButton.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { revalidateExpedientes } from "@/hooks/use-expedientes";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";

export function EvaluateButton({ expedienteId }: { expedienteId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleEvaluate() {
    setLoading(true);
    try {
      const result = await api.evaluate(expedienteId);
      await revalidateExpedientes();
      router.refresh();
      toast.success(`Evaluación completada — ${result.score_total} pts (${result.decision === "safe" ? "Aprobado" : result.decision === "review_required" ? "Revisión requerida" : "Alto riesgo"})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al evaluar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleEvaluate}
      disabled={loading}
      className="inline-flex items-center gap-2 justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all disabled:opacity-50"
    >
      <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
      {loading ? "Evaluando…" : "Evaluar ahora"}
    </button>
  );
}
```

- [ ] **Step 5.6: Update nuevo/page.tsx to use SWR mutate + toast**

Modify `frontend/app/expedientes/nuevo/page.tsx` — replace the `onSubmit` function:

```tsx
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const rfcErr = validateRfc(form.rfc);
    if (rfcErr) { setRfcError(rfcErr); return; }
    setLoading(true);
    setError(null);
    try {
      const expediente = await api.createExpediente(form);
      await revalidateExpedientes();
      router.push(`/expedientes/${expediente.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear expediente");
      setLoading(false);
    }
  }
```

Also add the import at the top of the file:

```tsx
import { revalidateExpedientes } from "@/hooks/use-expedientes";
```

- [ ] **Step 5.7: Commit**

```bash
rtk git add frontend/app/layout.tsx frontend/app/page.tsx frontend/components/ExpedientesList.tsx frontend/components/ExpedienteActions.tsx frontend/app/expedientes/[id]/reporte/EvaluateButton.tsx frontend/app/expedientes/nuevo/page.tsx
rtk git commit -m "feat(frontend): SWR real-time dashboard — mutations now update list instantly without F5"
```

---

## BLOCK D — UX/CRUD Polish

### Task 6: Add Sonner toasts + header cleanup

**Files:**
- Modify: `frontend/components/header.tsx`
- Modify: `frontend/app/layout.tsx` (add Toaster)

- [ ] **Step 6.1: Install Sonner via shadcn**

```bash
cd frontend && pnpm dlx shadcn@latest add sonner
```

- [ ] **Step 6.2: Add Toaster to layout**

Modify `frontend/app/layout.tsx` — add Toaster inside Providers:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Camtom KYB",
  description: "Plataforma KYB para agencia aduanal — Regla 1.4.14 RGCE 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>
          <Header />
          <div className="flex-1">{children}</div>
          <Toaster richColors position="bottom-right" />
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 6.3: Remove Admin SAT from header nav**

Full replacement of `frontend/components/header.tsx`:

```tsx
import Link from "next/link";

export function Header() {
  return (
    <header className="border-b border-border bg-background sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="font-bold text-primary text-lg tracking-tight">
          Camtom KYB
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link
            href="/"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Expedientes
          </Link>
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 6.4: Commit**

```bash
rtk git add frontend/components/header.tsx frontend/app/layout.tsx frontend/components/ui/sonner.tsx
rtk git commit -m "feat(frontend): add Sonner toasts, remove Admin from nav (not user-facing)"
```

---

### Task 7: Re-evaluate CTA when expediente needs_update

**Files:**
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`

- [ ] **Step 7.1: Read current report page**

Query codegraph for the current report page source:

```
codegraph_explore("expedientes id reporte page ReportPage fetch evaluation")
```

Then locate the section that renders the page top — add a `needs_update` banner before the score gauge.

- [ ] **Step 7.2: Add NeedsUpdateBanner component inline in report page**

After the page's existing imports and before the main return, add this component (it's only used in this file so keep it inline):

```tsx
function NeedsUpdateBanner({ expedienteId }: { expedienteId: string }) {
  return (
    <div className="rounded-xl border border-warning/40 bg-warning/5 px-5 py-4 flex items-start gap-3 mb-6">
      <AlertTriangle className="size-5 text-warning shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-warning">El expediente requiere actualización</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          Uno o más documentos han cambiado o vencido desde la última evaluación. Re-evaluá para obtener un resultado actualizado.
        </p>
      </div>
      <EvaluateButton expedienteId={expedienteId} />
    </div>
  );
}
```

Import `AlertTriangle` from `lucide-react` at the top of the file.

In the main page return, render `NeedsUpdateBanner` when `expediente.status === "needs_update"`:

```tsx
{expediente.status === "needs_update" && (
  <NeedsUpdateBanner expedienteId={expediente.id} />
)}
```

Place it immediately before the `ScoreGauge` section.

- [ ] **Step 7.3: Commit**

```bash
rtk git add frontend/app/expedientes/[id]/reporte/page.tsx
rtk git commit -m "feat(frontend): add re-evaluate banner when expediente status=needs_update"
```

---

## BLOCK C — Enriched KYB Report

### Task 8: Backend — evaluation history endpoint

**Files:**
- Modify: `backend/src/api/routers/expedientes.py`
- Modify: `frontend/lib/api-client.ts`

- [ ] **Step 8.1: Write a failing test for the new endpoint**

Add to `backend/src/tests/test_expedientes_router.py`:

```python
def test_list_evaluations_returns_history(client, sample_expediente_id):
    """GET /expedientes/{id}/evaluations returns list of past evaluations."""
    # Seed two evaluations
    from tests.conftest import fake_supabase
    fake_supabase._data["evaluations"] = [
        {"id": "ev-1", "expediente_id": sample_expediente_id, "score_total": 50,
         "decision": "review_required", "critical_blocks": [], "summary": {},
         "created_at": "2026-06-28T10:00:00Z"},
        {"id": "ev-2", "expediente_id": sample_expediente_id, "score_total": 0,
         "decision": "safe", "critical_blocks": [], "summary": {},
         "created_at": "2026-06-29T10:00:00Z"},
    ]
    resp = client.get(f"/expedientes/{sample_expediente_id}/evaluations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["decision"] == "safe"      # most recent first
    assert data[1]["decision"] == "review_required"
```

- [ ] **Step 8.2: Run test to confirm it fails**

```bash
cd backend && rtk test "uv run pytest src/tests/test_expedientes_router.py::test_list_evaluations_returns_history -v"
```

Expected: 404 (endpoint doesn't exist yet).

- [ ] **Step 8.3: Add the endpoint to expedientes router**

In `backend/src/api/routers/expedientes.py`, add after `get_latest_evaluation`:

```python
@router.get("/{expediente_id}/evaluations")
def list_evaluations(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = (
        supabase.table("evaluations")
        .select("id, score_total, decision, critical_blocks, created_at")
        .eq("expediente_id", expediente_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    return result.data
```

- [ ] **Step 8.4: Run test to confirm it passes**

```bash
cd backend && rtk test "uv run pytest src/tests/test_expedientes_router.py::test_list_evaluations_returns_history -v"
```

Expected: PASS.

- [ ] **Step 8.5: Run full backend test suite**

```bash
cd backend && rtk test "uv run pytest src/tests/ -v"
```

Expected: All tests pass.

- [ ] **Step 8.6: Add type + method to frontend api-client**

In `frontend/lib/api-client.ts`, add after the existing types:

```typescript
export type EvaluationHistoryEntry = {
  id: string;
  score_total: number;
  decision: Decision;
  critical_blocks: string[];
  created_at: string;
};
```

In the `api` object, add:

```typescript
  listEvaluations: (expedienteId: string): Promise<EvaluationHistoryEntry[]> =>
    request(`/expedientes/${expedienteId}/evaluations`),
```

- [ ] **Step 8.7: Commit**

```bash
rtk git add backend/src/api/routers/expedientes.py backend/src/tests/test_expedientes_router.py frontend/lib/api-client.ts
rtk git commit -m "feat(api): add GET /expedientes/{id}/evaluations — evaluation history endpoint with TDD"
```

---

### Task 9: Enriched report page — history + compliance context

**Files:**
- Create: `frontend/components/EvaluationHistory.tsx`
- Create: `frontend/components/ComplianceContext.tsx`
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`

- [ ] **Step 9.1: Create EvaluationHistory component**

Create `frontend/components/EvaluationHistory.tsx`:

```tsx
import type { EvaluationHistoryEntry, Decision } from "@/lib/api-client";
import { History, TrendingUp, TrendingDown, Minus } from "lucide-react";

const DECISION_LABEL: Record<Decision, { label: string; className: string }> = {
  safe: { label: "Aprobado", className: "text-success" },
  review_required: { label: "Revisión", className: "text-warning" },
  high_risk: { label: "Alto riesgo", className: "text-destructive" },
};

function TrendIcon({ current, prev }: { current: number; prev: number }) {
  if (current < prev) return <TrendingDown className="size-3.5 text-success" />;
  if (current > prev) return <TrendingUp className="size-3.5 text-destructive" />;
  return <Minus className="size-3.5 text-muted-foreground" />;
}

export function EvaluationHistory({ entries }: { entries: EvaluationHistoryEntry[] }) {
  if (entries.length <= 1) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <History className="size-4 text-muted-foreground" />
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Historial de evaluaciones
        </p>
      </div>

      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium">Fecha</th>
              <th className="text-center px-3 py-2 text-muted-foreground font-medium">Decisión</th>
              <th className="text-right px-3 py-2 text-muted-foreground font-medium">Score</th>
              <th className="text-center px-3 py-2 text-muted-foreground font-medium">Tendencia</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => {
              const cfg = DECISION_LABEL[entry.decision];
              const nextEntry = entries[i + 1];
              return (
                <tr key={entry.id} className="border-t border-border">
                  <td className="px-3 py-2 text-muted-foreground">
                    {new Date(entry.created_at).toLocaleString("es-MX", {
                      day: "2-digit", month: "short", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                    {i === 0 && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] font-medium">
                        Actual
                      </span>
                    )}
                  </td>
                  <td className={`px-3 py-2 text-center font-semibold ${cfg.className}`}>
                    {cfg.label}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-semibold">
                    {entry.score_total} pts
                  </td>
                  <td className="px-3 py-2 text-center">
                    {nextEntry ? (
                      <div className="flex items-center justify-center gap-1">
                        <TrendIcon current={entry.score_total} prev={nextEntry.score_total} />
                        <span className="text-muted-foreground">
                          {entry.score_total > nextEntry.score_total
                            ? `+${entry.score_total - nextEntry.score_total}`
                            : entry.score_total < nextEntry.score_total
                            ? `-${nextEntry.score_total - entry.score_total}`
                            : "="}
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 9.2: Create ComplianceContext component**

Create `frontend/components/ComplianceContext.tsx`:

```tsx
import { Scale, BookOpen, ExternalLink } from "lucide-react";

const REGLAS = [
  {
    titulo: "Regla 1.4.14 RGCE 2026",
    descripcion: "Requisito base que obliga a las agencias aduanales a verificar que sus clientes no figuren en las listas de contribuyentes incumplidos o EFOS del SAT antes de inscribirlos al Padrón de Importadores/Exportadores.",
    url: "https://www.sat.gob.mx/cs/Satellite?blobcol=urldata&blobkey=id&blobtable=MungoBlobs&blobwhere=1461172912385&ssbinary=true",
  },
  {
    titulo: "Art. 69 CFF — Contribuyentes incumplidos",
    descripcion: "Listado de personas físicas y morales con créditos fiscales firmes, exigibles, CSD sin efectos, o no localizadas. Presencia en este listado genera 25 pts de riesgo.",
    url: "https://www.sat.gob.mx/consultas/listado_69",
  },
  {
    titulo: "Art. 69-B CFF — EFOS (Empresas Facturadoras de Operaciones Simuladas)",
    descripcion: "El SAT publica dos sub-listados: 'presuntos' (proceso de revisión, 40 pts de riesgo) y 'definitivos' (bloqueo crítico — no operar bajo ninguna circunstancia, 100 pts). La desvirtualización ante el SAT es el único camino para salir del listado definitivo.",
    url: "https://www.sat.gob.mx/consultas/listado_69b",
  },
  {
    titulo: "Art. 69-B Bis CFF — Transmisión indebida de pérdidas",
    descripcion: "Listado de contribuyentes que transfirieron pérdidas fiscales de forma indebida. Genera 35 pts de riesgo. Requiere aclaración ante el SAT y resolución formal antes de operar.",
    url: "https://www.sat.gob.mx/consultas/listado_69b_bis",
  },
  {
    titulo: "Art. 49 Bis CFF — Contrabando técnico",
    descripcion: "No tiene lista pública consultable al día de hoy. El sistema lo documenta como limitación conocida y lo marca como 'revisión manual requerida'. No genera puntos de riesgo automáticos.",
    url: null,
  },
  {
    titulo: "LFPIORPI — Beneficiario Controlador",
    descripcion: "La Ley Federal para la Prevención e Identificación de Operaciones con Recursos de Procedencia Ilícita exige identificar al beneficiario controlador (persona física con ≥25% del capital o control efectivo de la empresa). Su omisión genera 20 pts de riesgo.",
    url: null,
  },
];

export function ComplianceContext() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Scale className="size-4 text-muted-foreground" />
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Marco legal y regulatorio
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card/40 p-4 space-y-1">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Este reporte evalúa el cumplimiento de la{" "}
          <span className="font-semibold text-foreground">Regla 1.4.14 RGCE 2026</span>
          , que exige a las agencias aduanales realizar diligencia KYB (Know Your Business) antes de inscribir a un cliente en el Padrón de Importadores/Exportadores. Un score &lt;30 permite la inscripción; entre 30 y 69 exige diligencia ampliada; ≥70 bloquea la inscripción.
        </p>
      </div>

      <div className="space-y-2">
        {REGLAS.map((regla) => (
          <details key={regla.titulo} className="group rounded-lg border border-border bg-card">
            <summary className="flex items-center gap-2 cursor-pointer px-4 py-3 text-xs font-medium text-foreground hover:bg-muted/30 transition-colors list-none select-none">
              <BookOpen className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1">{regla.titulo}</span>
              <span className="text-muted-foreground group-open:rotate-90 transition-transform">›</span>
            </summary>
            <div className="px-4 pb-3 pt-0 space-y-2">
              <p className="text-xs text-muted-foreground leading-relaxed">{regla.descripcion}</p>
              {regla.url && (
                <a
                  href={regla.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="size-3" />
                  Consultar en fuente oficial (SAT)
                </a>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 9.3: Update report page to include history + compliance context**

Read the current report page via codegraph, then modify `frontend/app/expedientes/[id]/reporte/page.tsx` to:

1. Fetch evaluation history alongside the existing data:

```tsx
const [expediente, evaluation, historialEvals] = await Promise.all([
  api.getExpediente(params.id),
  api.getLatestEvaluation(params.id),
  api.listEvaluations(params.id),
]);
```

2. Add imports:

```tsx
import { EvaluationHistory } from "@/components/EvaluationHistory";
import { ComplianceContext } from "@/components/ComplianceContext";
```

3. Add sections in the report page after the ActionCard list and before the page end:

```tsx
{/* Evaluation history (only shown if >1 evaluation) */}
{historialEvals.length > 1 && (
  <section>
    <EvaluationHistory entries={historialEvals} />
  </section>
)}

{/* Legal + compliance context */}
<section>
  <ComplianceContext />
</section>
```

- [ ] **Step 9.4: Verify the report page compiles**

```bash
cd frontend && pnpm build 2>&1 | tail -20
```

Expected: Build succeeds with no type errors.

- [ ] **Step 9.5: Commit**

```bash
rtk git add frontend/components/EvaluationHistory.tsx frontend/components/ComplianceContext.tsx frontend/app/expedientes/[id]/reporte/page.tsx frontend/lib/api-client.ts
rtk git commit -m "feat(report): add evaluation history + RGCE 1.4.14 compliance context panel"
```

---

## Final Integration Check

- [ ] **Step 10.1: Run full backend test suite**

```bash
cd backend && rtk test "uv run pytest src/tests/ -v"
```

Expected: All tests pass.

- [ ] **Step 10.2: Run frontend build**

```bash
cd frontend && pnpm build
```

Expected: No type errors, no build failures.

- [ ] **Step 10.3: Seed demo data and test locally**

```bash
cd backend && uv run python scripts/seed_demo_data.py
cd frontend && pnpm dev
```

Open http://localhost:3000. Verify:
- Dashboard shows 3 expedientes after seeding without F5
- Edit expediente → list updates instantly
- Delete expediente → row disappears instantly
- Go to a report → score and factors show correctly
- Evaluate → toast appears, score updates
- Report shows compliance context and history (if >1 evaluation)
- Admin SAT is NOT in the nav

- [ ] **Step 10.4: Save session summary to engram**

```
mem_session_summary(
  goal="KYB professional overhaul",
  discoveries=["rfc_formato_invalido special case bug fixed", "demo PDFs were missing 4 doc types", "dashboard was Server Component needing SWR for real-time"],
  accomplished=["Scoring fix", "Complete demo PDFs (8 types)", "Seed script", "SWR real-time", "Sonner toasts", "Header cleanup", "re-evaluate banner", "Eval history endpoint + UI", "Compliance context panel"],
  next_steps=["Deploy to Vercel", "Run seed_demo_data.py against production Supabase"],
  relevant_files=[...]
)
```

- [ ] **Step 10.5: Push and create PR**

```bash
rtk git push
```

Then create PR via `gh pr create`.
