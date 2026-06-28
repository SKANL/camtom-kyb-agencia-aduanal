"""
Generate synthetic, text-selectable PDF documents for the 3 demo expedientes.

Output: backend/scripts/demo_pdfs/
  expediente_1_safe/
    csf.pdf, acta_constitutiva.pdf, comprobante_domicilio.pdf,
    identificacion_rep_legal.pdf, encargo_conferido.pdf, manifestacion_protesta.pdf
  expediente_2_review_required/  (same set, with intentional discrepancies)
  expediente_3_high_risk/        (minimal - blocking is via SAT list, not docs)

Usage:
  cd backend && uv run python scripts/generate_demo_pdfs.py

Then upload each PDF via the UI (Task 5.5) or via the API.

Note: dates use the current month/year so freshness checks pass at demo time.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from fpdf import FPDF


def _pdf(lines: list[str], output_path: Path) -> None:
    """Write a minimal A4 PDF with selectable text. No images."""
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        if line.startswith("# "):
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(0, 10, line[2:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=11)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.cell(0, 8, line[3:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=11)
        elif line == "---":
            pdf.ln(3)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, line or " ", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


today = date.today()
current_month = today.strftime("%m/%Y")
recent_date = (today - timedelta(days=10)).strftime("%d/%m/%Y")
old_date = (today - timedelta(days=120)).strftime("%d/%m/%Y")  # >90 días - triggers review_required


# ─── Expediente 1: SAFE ──────────────────────────────────────────────────────
E1_RFC = "EKU9003173C9"
E1_RAZON = "Escuela Kemper Urgate SA de CV"
E1_DOMICILIO = "Av. Insurgentes Sur 123, Col. Roma, CDMX"
E1_REP = "Juan Pérez García"

EXPEDIENTE_1: dict[str, list[str]] = {
    "csf": [
        "# Constancia de Situación Fiscal",
        "Servicio de Administración Tributaria",
        "---",
        f"RFC: {E1_RFC}",
        f"Razón Social: {E1_RAZON}",
        f"Domicilio Fiscal: {E1_DOMICILIO}",
        f"Fecha de emisión: {recent_date}",
        "Régimen Fiscal: 601 - General de Ley Personas Morales",
        "Situación: Activo",
        "---",
        "Este documento acredita la situación fiscal ante el SAT.",
    ],
    "acta_constitutiva": [
        "# Acta Constitutiva",
        f"Empresa: {E1_RAZON}",
        f"RFC: {E1_RFC}",
        "---",
        "Instrumento notarial número 12,345 de fecha 15/03/2010.",
        "Notario Público núm. 42, Lic. Roberto Solís, CDMX.",
        "Objeto social: Servicios educativos.",
        "Capital social: $500,000.00 MXN.",
        "---",
        "Socios fundadores:",
        f"  - {E1_REP} (51%)",
        "  - Ana García Ramírez (49%)",
    ],
    "comprobante_domicilio": [
        "# Comprobante de Domicilio",
        "Comisión Federal de Electricidad",
        "---",
        f"Titular: {E1_RAZON}",
        f"Domicilio: {E1_DOMICILIO}",
        f"Fecha de emisión: {recent_date}",
        "Período facturado: bimestre vigente",
        "Número de cuenta: 1234-5678-9012",
        "Monto: $1,250.00 MXN",
        "---",
        "Comprobante válido como identificación de domicilio fiscal.",
    ],
    "identificacion_rep_legal": [
        "# Identificación Oficial - Representante Legal",
        "Instituto Nacional Electoral",
        "---",
        f"Nombre: {E1_REP}",
        "CURP: PEGJ800101HDFRZN08",
        f"Vigencia: {(today.replace(year=today.year + 3)).strftime('%d/%m/%Y')}",
        "Clave de elector: PEREZU80010112H000",
        "Sección: 1234 - Distrito Federal 05",
        "---",
        "Documento oficial con validez en todo el territorio nacional.",
    ],
    "encargo_conferido": [
        "# Encargo Conferido",
        "Agente Aduanal - Autorización de Representación",
        "---",
        "Importador/Exportador:",
        f"  Razón Social: {E1_RAZON}",
        f"  RFC: {E1_RFC}",
        "---",
        "Agente Aduanal autorizado:",
        "  RFC Agente: LOAM750312AB3",
        "  Patente: 3456",
        "Alcance: Importacion y exportacion - todas las fracciones arancelarias.",
        f"Vigencia: {(today.replace(year=today.year + 1)).strftime('%d/%m/%Y')}",
        "---",
        f"Firma del Representante Legal: {E1_REP}",
        f"Fecha de firma: {recent_date}",
    ],
    "manifestacion_protesta": [
        "# Manifestación bajo Protesta de Decir Verdad",
        "Regla 1.4.14 RGCE 2026",
        "---",
        f"Empresa: {E1_RAZON}",
        f"RFC: {E1_RFC}",
        f"Representante Legal: {E1_REP}",
        "---",
        "DECLARO BAJO PROTESTA DE DECIR VERDAD que la empresa que represento:",
        "",
        "1. NO se encuentra en el listado del Artículo 69-B del CFF (empresas que",
        "   facturan operaciones simuladas - EFOS definitivos).",
        "2. NO se encuentra en el Artículo 49 Bis (contrabando técnico).",
        "3. Toda la información proporcionada es verídica y comprobable.",
        "---",
        f"Lugar y fecha: Ciudad de México, {recent_date}",
        f"Firma: {E1_REP}",
    ],
}

# ─── Expediente 2: REVIEW REQUIRED ───────────────────────────────────────────
# Discrepancias: razón social y domicilio ligeramente distintos + comprobante >90 días
E2_RFC = "COX010101AB1"
E2_RAZON_FORMULARIO = "Corporativo X"           # En el formulario
E2_RAZON_CSF = "Corporativo X SA de CV"         # En la CSF - discrepancia
E2_DOMICILIO_FORM = "Avenida Insurgentes Sur Num 123, Colonia Roma"
E2_DOMICILIO_CSF = "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX"  # distinto
E2_REP = "María López"

EXPEDIENTE_2: dict[str, list[str]] = {
    "csf": [
        "# Constancia de Situación Fiscal",
        "Servicio de Administración Tributaria",
        "---",
        f"RFC: {E2_RFC}",
        f"Razón Social: {E2_RAZON_CSF}",          # "SA de CV" que falta en el formulario
        f"Domicilio Fiscal: {E2_DOMICILIO_CSF}",
        f"Fecha de emisión: {recent_date}",
        "Régimen Fiscal: 601 - General de Ley Personas Morales",
        "Situación: Activo",
        "---",
        "NOTA: La razón social exacta es 'Corporativo X SA de CV'.",
        "La omisión del tipo societario en solicitudes es causa de revisión.",
    ],
    "acta_constitutiva": [
        "# Acta Constitutiva",
        f"Empresa: {E2_RAZON_CSF}",
        f"RFC: {E2_RFC}",
        "---",
        "Instrumento notarial número 7,890 de fecha 20/06/2015.",
        "Notario Público núm. 15, Lic. Carmen Vidal, CDMX.",
        "Objeto social: Consultoría empresarial.",
        "Capital social: $1,000,000.00 MXN.",
        "---",
        "Socios fundadores:",
        f"  - {E2_REP} (60%)",
        "  - Roberto Mendoza Cruz (40%)",
    ],
    "comprobante_domicilio": [
        "# Comprobante de Domicilio",
        "Telmex - Servicios de Telecomunicaciones",
        "---",
        f"Titular: {E2_RAZON_CSF}",
        f"Domicilio: {E2_DOMICILIO_FORM}",          # domicilio distinto al de CSF
        f"Fecha de emisión: {old_date}",             # >90 días - triggers review
        "Período facturado: bimestre anterior",
        "Número de cuenta: 9876-5432-1098",
        "Monto: $890.00 MXN",
        "---",
        "ADVERTENCIA: Este comprobante puede estar próximo a vencer.",
        "Se recomienda actualizar con uno reciente.",
    ],
    "identificacion_rep_legal": [
        "# Identificación Oficial - Representante Legal",
        "Instituto Nacional Electoral",
        "---",
        f"Nombre: {E2_REP}",
        "CURP: LOCM850615MDFPZR05",
        f"Vigencia: {(today.replace(year=today.year + 2)).strftime('%d/%m/%Y')}",
        "Clave de elector: LOPEZM85061512H000",
        "Sección: 5678 - Distrito Federal 09",
    ],
    "encargo_conferido": [
        "# Encargo Conferido",
        "Agente Aduanal - Autorización de Representación",
        "---",
        "Importador/Exportador:",
        f"  Razón Social: {E2_RAZON_CSF}",
        f"  RFC: {E2_RFC}",
        "---",
        "Agente Aduanal autorizado:",
        "  RFC Agente: GAMA820930CD5",
        "  Patente: 1122",
        "Alcance: Importación - capítulos 1-24 del arancel.",
        f"Vigencia: {(today.replace(year=today.year + 1)).strftime('%d/%m/%Y')}",
        "---",
        f"Firma del Representante Legal: {E2_REP}",
        f"Fecha de firma: {recent_date}",
    ],
    "manifestacion_protesta": [
        "# Manifestación bajo Protesta de Decir Verdad",
        "Regla 1.4.14 RGCE 2026",
        "---",
        f"Empresa: {E2_RAZON_CSF}",
        f"RFC: {E2_RFC}",
        f"Representante Legal: {E2_REP}",
        "---",
        "DECLARO BAJO PROTESTA DE DECIR VERDAD que la empresa que represento",
        "no se encuentra en los listados del Artículo 69-B ni 49 Bis del CFF,",
        "y que toda la información es veraz y verificable.",
        "---",
        f"Lugar y fecha: Ciudad de México, {recent_date}",
        f"Firma: {E2_REP}",
    ],
}

# ─── Expediente 3: HIGH RISK ──────────────────────────────────────────────────
# RFC real en listado 69-B Definitivos - el bloqueo es por listas SAT, no docs
# RFC se lee del entorno para no hardcodear uno que podría caducar del listado.
E3_RFC = os.environ.get("DEMO_RFC_HIGH_RISK", "PLACEHOLDER_RFC_69B")
E3_RAZON = "Empresa en Lista Negra SA de CV"
E3_REP = "Carlos Sánchez"

EXPEDIENTE_3: dict[str, list[str]] = {
    "csf": [
        "# Constancia de Situación Fiscal",
        "Servicio de Administración Tributaria",
        "---",
        f"RFC: {E3_RFC}",
        f"Razón Social: {E3_RAZON}",
        "Domicilio Fiscal: Calle Reforma 456, Col. Centro, CDMX",
        f"Fecha de emisión: {recent_date}",
        "Régimen Fiscal: 601 - General de Ley Personas Morales",
        "Situación: Activo",
        "---",
        "NOTA: Este RFC aparece en el listado Art. 69-B Definitivos del SAT.",
        "La evaluación KYB resultará en high_risk.",
    ],
    "manifestacion_protesta": [
        "# Manifestación bajo Protesta de Decir Verdad",
        "Regla 1.4.14 RGCE 2026",
        "---",
        f"Empresa: {E3_RAZON}",
        f"RFC: {E3_RFC}",
        f"Representante Legal: {E3_REP}",
        "---",
        "DECLARO BAJO PROTESTA DE DECIR VERDAD que la empresa que represento",
        "no se encuentra en los listados del Artículo 69-B ni 49 Bis del CFF.",
        "---",
        f"Lugar y fecha: Ciudad de México, {recent_date}",
        f"Firma: {E3_REP}",
    ],
}


def main():
    base = Path(__file__).parent / "demo_pdfs"

    expedientes = [
        ("expediente_1_safe", EXPEDIENTE_1),
        ("expediente_2_review_required", EXPEDIENTE_2),
        ("expediente_3_high_risk", EXPEDIENTE_3),
    ]

    for folder, docs in expedientes:
        for doc_type, lines in docs.items():
            out = base / folder / f"{doc_type}.pdf"
            _pdf(lines, out)
            print(f"  Generated: {out}")

    print(f"\nPDFs written to: {base}")
    print("\nNext: upload each PDF via the UI (or POST /documentos) for its expediente.")
    if E3_RFC == "PLACEHOLDER_RFC_69B":
        print(
            "\nWARNING: DEMO_RFC_HIGH_RISK not set. "
            "Set it to a real RFC from the 69-B definitivos list before uploading Expediente 3 docs.\n"
            "  e.g.: DEMO_RFC_HIGH_RISK=XYZABC123456 uv run python scripts/generate_demo_pdfs.py"
        )


if __name__ == "__main__":
    main()
