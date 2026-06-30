from infrastructure.ai.groq_client import get_groq_model
from infrastructure.ai.harness import call_with_harness
from infrastructure.ai.schemas import SCHEMA_REGISTRY

PROMPT_EXTRACCION = (
    "Eres un extractor de datos de documentos fiscales y legales mexicanos. "
    "Extrae SOLO lo que aparece literalmente en el texto. Si un campo no esta "
    "presente, devuelve null. Normaliza fechas a ISO 8601. No inventes RFCs ni "
    "datos que no esten en el texto.\n\nTexto del documento:\n{texto}"
)

# Per-doc-type hints appended to the base prompt to guide structured field extraction
DOC_TYPE_HINTS: dict[str, str] = {
    "manifestacion_protesta": (
        "\n\nINSTRUCCION ESPECIAL para el campo 'declara_no_69b_49bis': "
        "Devuelve TRUE si el documento contiene clausulas que declaren EXPLICITAMENTE "
        "que la empresa NO esta en los supuestos del Art. 69-B CFF (EFOS) ni en el "
        "Art. 49 Bis CFF (frases como: 'no se encuentra en los supuestos', "
        "'no ha transmitido indebidamente perdidas fiscales', "
        "'no realiza operaciones de contrabando tecnico'). "
        "Devuelve FALSE si el documento afirma que SI esta en esas listas. "
        "Devuelve null si el documento no menciona el Art. 69-B ni el Art. 49 Bis CFF."
    ),
    "acta_constitutiva": (
        "\n\nINSTRUCCION ESPECIAL para el campo 'socios': "
        "Extrae la lista de socios/accionistas como objetos con tres campos: "
        "'nombre' (nombre completo de la persona), "
        "'rfc' (RFC de 12 o 13 caracteres — devuelve null si no aparece en el documento), "
        "'porcentaje' (numero de participacion, ej: 60 para 60%). "
        "Ejemplo de salida: "
        "[{\"nombre\": \"Juan Perez Garcia\", \"rfc\": \"PEGJ850101HDFRZN09\", \"porcentaje\": 60}]. "
        "Si el porcentaje aparece como texto '60%', extrae solo el numero 60. "
        "Si hay multiples socios, incluye todos en la lista."
    ),
}


def extraer_campos(supabase_client, doc_type: str, texto: str) -> dict:
    schema_cls = SCHEMA_REGISTRY[doc_type]
    hint = DOC_TYPE_HINTS.get(doc_type, "")

    def compute() -> dict:
        modelo = get_groq_model("extraction").with_structured_output(schema_cls)
        prompt = (PROMPT_EXTRACCION + hint).format(texto=texto)
        return modelo.invoke(prompt).model_dump()

    return call_with_harness(
        supabase_client,
        "extraction",
        {"doc_type": doc_type, "texto": texto},
        compute,
    )
