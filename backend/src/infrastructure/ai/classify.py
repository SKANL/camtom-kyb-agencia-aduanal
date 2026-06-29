import json
import logging

from langchain_core.messages import HumanMessage

from infrastructure.ai.groq_client import get_groq_model

logger = logging.getLogger(__name__)

VALID_DOC_TYPES = {
    "csf", "acta_constitutiva", "comprobante_domicilio",
    "identificacion_rep_legal", "poder_notarial",
    "encargo_conferido", "manifestacion_protesta",
}

_PROMPT = """You are a document classification assistant for a Mexican customs agency KYB system.
Read the following document text and identify its type.

Document types:
- csf: Constancia de Situación Fiscal (SAT tax status certificate)
- acta_constitutiva: Acta Constitutiva (articles of incorporation)
- comprobante_domicilio: Comprobante de Domicilio (proof of address — CFE, Telmex, water, etc.)
- identificacion_rep_legal: Identificación Oficial del Representante Legal (INE, pasaporte)
- poder_notarial: Poder Notarial (notarial power of attorney)
- encargo_conferido: Encargo Conferido (customs agent authorization letter, patente aduanal)
- manifestacion_protesta: Manifestación bajo Protesta de Decir Verdad (Regla 1.4.14 declaration)

Return ONLY valid JSON with no extra text:
{{"doc_type": "<one of the types above or 'unknown'>", "confidence": "<high or low>"}}

Use "high" confidence when the document clearly matches one type.
Use "low" when unsure.

Document text (first 2000 chars):
{text}"""


def clasificar_documento(texto: str) -> dict:
    """Classify a document by its text content. Returns {doc_type, confidence}."""
    try:
        llm = get_groq_model()
        prompt = _PROMPT.format(text=texto[:2000])
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        doc_type = data.get("doc_type", "unknown")
        confidence = data.get("confidence", "low")
        if doc_type not in VALID_DOC_TYPES:
            doc_type = "unknown"
            confidence = "low"
        if confidence not in ("high", "low"):
            confidence = "low"
        return {"doc_type": doc_type, "confidence": confidence}
    except Exception as exc:
        logger.warning("clasificar_documento failed: %s", exc, exc_info=True)
        return {"doc_type": "unknown", "confidence": "low"}
