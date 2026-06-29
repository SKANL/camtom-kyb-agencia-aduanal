"""Generate 3 text-selectable synthetic PDFs for KYB demo scenarios."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path(__file__).parent / "demo_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)


def make_csf(path: Path, rfc: str, razon_social: str, domicilio: str, rep_legal: str):
    """Constancia de Situación Fiscal (simplified SAT format)."""
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
        ("Fecha de emisión:", "2026-06-01"),
        ("Estatus en el RFC:", "ACTIVO"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(7 * cm, y, value)
        y -= 0.8 * cm

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_acta(path: Path, rfc: str, razon_social: str, rep_legal: str, socios: list[str]):
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "ACTA CONSTITUTIVA")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 2.7 * cm, "Sociedad Anónima de Capital Variable")

    c.setFont("Helvetica", 9)
    y = h - 4 * cm
    lines = [
        f"En la Ciudad de México, siendo las 10:00 horas del 1 de enero de 2015, comparecen:",
        f"Razón Social: {razon_social}",
        f"RFC: {rfc}",
        f"Representante Legal: {rep_legal}",
        "",
        "SOCIOS / ACCIONISTAS:",
    ]
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.65 * cm
    for socio in socios:
        c.drawString(2.5 * cm, y, f"• {socio}")
        y -= 0.65 * cm

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_comprobante_domicilio(path: Path, razon_social: str, domicilio: str, fecha: str):
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

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_manifestacion(path: Path, razon_social: str, rfc: str, rep_legal: str, declara: bool):
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
    # Word-wrap basic
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
            "1. La empresa cumple con sus obligaciones fiscales.",
            "2. Toda la información proporcionada es verídica.",
        ]

    for clausula in clausulas:
        c.drawString(2 * cm, y, clausula)
        y -= 0.65 * cm

    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Firma: ________________________    Fecha: 2026-06-15")

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def generate():
    # ── Scenario 1: CLEAN — EKU9003173C9 ──────────────────────────────────────
    clean_dir = OUTPUT_DIR / "escenario_1_limpio"
    clean_dir.mkdir(exist_ok=True)
    make_csf(
        clean_dir / "csf.pdf",
        rfc="EKU9003173C9",
        razon_social="Escuela Kemper Urgate SA de CV",
        domicilio="Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        rep_legal="Juan Pérez García",
    )
    make_acta(
        clean_dir / "acta_constitutiva.pdf",
        rfc="EKU9003173C9",
        razon_social="Escuela Kemper Urgate SA de CV",
        rep_legal="Juan Pérez García",
        socios=["Juan Pérez García (60%)", "María López Ramírez (40%)"],
    )
    make_comprobante_domicilio(
        clean_dir / "comprobante_domicilio.pdf",
        razon_social="Escuela Kemper Urgate SA de CV",
        domicilio="Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        fecha="2026-06-01",
    )
    make_manifestacion(
        clean_dir / "manifestacion_protesta.pdf",
        razon_social="Escuela Kemper Urgate SA de CV",
        rfc="EKU9003173C9",
        rep_legal="Juan Pérez García",
        declara=True,
    )

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    disc_dir = OUTPUT_DIR / "escenario_2_discrepancia"
    disc_dir.mkdir(exist_ok=True)
    make_csf(
        disc_dir / "csf.pdf",
        rfc="COX010101AB1",
        razon_social="Corporativo X SA de CV",            # canonical name
        domicilio="Avenida Insurgentes Sur Num 123, Colonia Roma",
        rep_legal="María López",
    )
    make_acta(
        disc_dir / "acta_constitutiva.pdf",
        rfc="COX010101AB1",
        razon_social="Corporativo X, S.A. de C.V.",       # slight variation → disc_razon_social
        rep_legal="Maria Lopez Hernandez",                 # full name → disc_representante match
        socios=["María López Hernandez (51%)", "Roberto Sánchez Cruz (49%)"],
    )
    make_comprobante_domicilio(
        disc_dir / "comprobante_domicilio.pdf",
        razon_social="Corporativo X SA de CV",
        domicilio="Insurgentes Sur 123, Roma",             # variation → disc_domicilio
        fecha="2026-06-01",
    )
    make_manifestacion(
        disc_dir / "manifestacion_protesta.pdf",
        razon_social="Corporativo X SA de CV",
        rfc="COX010101AB1",
        rep_legal="María López",
        declara=True,
    )

    # ── Scenario 3: HIGH RISK — AAA120730823 (69-B Definitivos) ───────────────
    risk_dir = OUTPUT_DIR / "escenario_3_alto_riesgo"
    risk_dir.mkdir(exist_ok=True)
    make_csf(
        risk_dir / "csf.pdf",
        rfc="AAA120730823",
        razon_social="Empresa en Lista Negra SA de CV",
        domicilio="Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        rep_legal="Carlos Sánchez",
    )
    make_acta(
        risk_dir / "acta_constitutiva.pdf",
        rfc="AAA120730823",
        razon_social="Empresa en Lista Negra SA de CV",
        rep_legal="Carlos Sánchez",
        socios=["Carlos Sánchez (100%)"],
    )
    make_comprobante_domicilio(
        risk_dir / "comprobante_domicilio.pdf",
        razon_social="Empresa en Lista Negra SA de CV",
        domicilio="Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        fecha="2026-06-01",
    )
    make_manifestacion(
        risk_dir / "manifestacion_protesta.pdf",
        razon_social="Empresa en Lista Negra SA de CV",
        rfc="AAA120730823",
        rep_legal="Carlos Sánchez",
        declara=False,   # missing 69-B/49-Bis clauses → manifestacion_incompleta
    )

    print("Demo PDFs generated:")
    for f in sorted(OUTPUT_DIR.rglob("*.pdf")):
        print(f"  {f.relative_to(OUTPUT_DIR.parent.parent)}")


if __name__ == "__main__":
    generate()
