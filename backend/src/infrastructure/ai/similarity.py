from infrastructure.ai.groq_client import get_groq_model
from infrastructure.ai.schemas import SimilarityResult
from infrastructure.ai.harness import call_with_harness

PROMPT_SIMILARITY = (
    "Compara estas dos cadenas que representan {campo} de una empresa mexicana. "
    "Considera abreviaturas legales equivalentes (SA de CV = S.A. de C.V.), acentos, "
    "mayusculas y orden de tokens. No penalices diferencias puramente ortograficas.\n"
    "Texto A: {texto_a}\nTexto B: {texto_b}"
)


def comparar_semanticamente(supabase_client, campo: str, texto_a: str, texto_b: str) -> dict:
    def compute() -> dict:
        modelo = get_groq_model("similarity").with_structured_output(SimilarityResult)
        return modelo.invoke(
            PROMPT_SIMILARITY.format(campo=campo, texto_a=texto_a, texto_b=texto_b)
        ).model_dump()

    return call_with_harness(
        supabase_client,
        "similarity",
        {"campo": campo, "texto_a": texto_a, "texto_b": texto_b},
        compute,
    )
