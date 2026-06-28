from infrastructure.ai.groq_client import get_groq_model
from infrastructure.ai.harness import call_with_harness
from infrastructure.ai.schemas import SCHEMA_REGISTRY

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

    return call_with_harness(
        supabase_client,
        "extraction",
        {"doc_type": doc_type, "texto": texto},
        compute,
    )
