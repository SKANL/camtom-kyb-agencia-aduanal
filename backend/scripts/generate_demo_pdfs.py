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


def make_comprobante_rfc(path: Path, rfc: str, razon_social: str, domicilio: str = ""):
    """Comprobante de RFC (cédula de identificación fiscal)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "CÉDULA DE IDENTIFICACIÓN FISCAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Servicio de Administración Tributaria")
    fields = [
        ("RFC:", rfc),
        ("Razón Social:", razon_social),
        ("Domicilio Fiscal:", domicilio),
        ("Tipo de persona:", "Moral"),
        ("Fecha de alta en RFC:", "2015-01-15"),
        ("Régimen Fiscal:", "601 - General de Ley Personas Morales"),
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
    make_comprobante_rfc(clean_dir / "rfc.pdf", "EKU9003173C9", "Escuela Kemper Urgate SA de CV",
                         "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700")

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    # All 8 docs. Intentional mismatches in razon_social + representante.
    # Expected scoring: disc_razon_social (30) + disc_representante (25) = 55 pts → review_required
    disc_dir = OUTPUT_DIR / "escenario_2_discrepancia"
    disc_dir.mkdir(exist_ok=True)
    make_csf(disc_dir / "csf.pdf", "COX010101AB1", "Corporativo Equis Distribuidora, SA de CV",
             "Avenida Insurgentes Sur Num 123, Colonia Roma", "María López")
    make_acta(disc_dir / "acta_constitutiva.pdf", "COX010101AB1", "Corporativo X, S.A. de C.V.",
              "Maria Lopez Hernandez", ["María López Hernandez (51%)", "Roberto Sánchez Cruz (49%)"])
    make_comprobante_domicilio(disc_dir / "comprobante_domicilio.pdf", "Corporativo X SA de CV",
                               "Insurgentes Sur 123, Roma", "2026-06-01")
    make_manifestacion(disc_dir / "manifestacion_protesta.pdf", "Corporativo X SA de CV",
                       "COX010101AB1", "María López", declara=True)
    make_identificacion_rep_legal(disc_dir / "identificacion_rep_legal.pdf", "Maria Lopez Hernandez")
    make_poder_notarial(disc_dir / "poder_notarial.pdf", "Carlos Eduardo Morales Ríos",
                        "Corporativo X SA de CV")
    make_encargo_conferido(disc_dir / "encargo_conferido.pdf", "CAMT930401AB9", "Corporativo X SA de CV")
    make_comprobante_rfc(disc_dir / "rfc.pdf", "COX010101AB1", "Corporativo X SA de CV",
                         "Avenida Insurgentes Sur Num 123, Colonia Roma")

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
    make_comprobante_rfc(risk_dir / "rfc.pdf", "AAA120730823", "Empresa en Lista Negra SA de CV",
                         "Calle Reforma 456, Col. Centro, CDMX, CP 06000")

    print("Demo PDFs generated:")
    for f in sorted(OUTPUT_DIR.rglob("*.pdf")):
        print(f"  {f.relative_to(OUTPUT_DIR.parent.parent)}")


if __name__ == "__main__":
    generate()
