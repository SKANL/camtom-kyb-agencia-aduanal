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
    "csf": (
        "\n\nINSTRUCCION para CSF: El campo 'rfc' contiene el identificador fiscal de 12-13 chars "
        "(formato: 3 letras + 6 digitos de fecha + 3 caracteres homonimia, ej: EKU9003173C9). "
        "El campo 'razon_social' es el nombre completo de la empresa o persona moral. "
        "El campo 'fecha_emision' es la fecha en que se generó este documento (ISO 8601 YYYY-MM-DD). "
        "Busca estos valores junto a etiquetas como 'RFC:', 'Razón Social:', 'Fecha de emisión:'."
    ),
    "rfc": (
        "\n\nINSTRUCCION para Cédula RFC: El campo 'rfc' es el RFC de 12-13 chars de la empresa. "
        "El campo 'razon_social' es el nombre o razón social completo. "
        "El campo 'domicilio_fiscal' es la dirección fiscal completa. "
        "Busca etiquetas como 'RFC:', 'Razón Social:', 'Domicilio Fiscal:'."
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
        "Si hay multiples socios, incluye todos en la lista. "
        "El campo 'rfc' de nivel superior es el RFC de la empresa (no de los socios). "
        "El campo 'razon_social' es el nombre de la empresa."
    ),
    "comprobante_domicilio": (
        "\n\nINSTRUCCION para Comprobante de Domicilio: El campo 'fecha_emision' es la fecha "
        "de emisión/generación del documento (ISO 8601 YYYY-MM-DD). "
        "Busca etiquetas como 'Fecha de emisión:', 'Fecha:', 'Periodo:'. "
        "El campo 'domicilio' es la dirección completa del titular."
    ),
    "identificacion_rep_legal": (
        "\n\nINSTRUCCION para ID del Representante Legal: El campo 'nombre_completo' es el nombre "
        "completo de la persona tal como aparece en el documento (INE, pasaporte, etc.). "
        "Busca etiquetas como 'Nombre:', 'Nombre Completo:', 'NOMBRE:'. "
        "El campo 'fecha_vencimiento' es la fecha de vencimiento del documento (ISO 8601)."
    ),
    "poder_notarial": (
        "\n\nINSTRUCCION para Poder Notarial: El campo 'nombre_representante' es el nombre "
        "completo de la persona a quien se le otorga el poder. "
        "Busca frases como 'otorga poder... a:', 'Nombre del Representante:', 'apoderado:'. "
        "El campo 'alcance' describe el tipo o ámbito del poder (ej: 'Actos de Administración y Dominio')."
    ),
    "encargo_conferido": (
        "\n\nINSTRUCCION para Encargo Conferido: El campo 'rfc_agente_aduanal' es el RFC del "
        "agente aduanal (12-13 chars). Busca 'RFC Agente Aduanal:', 'RFC:', 'Agente:'. "
        "El campo 'fecha_vigencia' es la fecha hasta la que es válido el encargo (ISO 8601). "
        "El campo 'alcance' describe el tipo de operaciones autorizadas."
    ),
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
