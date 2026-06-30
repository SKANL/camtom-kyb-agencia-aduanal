import os
from langchain_groq import ChatGroq

# Task-specific model selection — override via environment variables for flexibility
_MODELS: dict[str, str] = {
    "classification": os.environ.get("GROQ_MODEL_CLASSIFICATION", "llama-3.1-8b-instant"),
    "extraction": os.environ.get("GROQ_MODEL_EXTRACTION", "llama-3.3-70b-versatile"),
    "similarity": os.environ.get("GROQ_MODEL_SIMILARITY", "qwen/qwen3-32b"),
}

# Keep for backward compatibility — defaults to extraction model
MODEL_EXTRACCION = _MODELS["extraction"]


def get_groq_model(task: str = "extraction") -> ChatGroq:
    """Return a ChatGroq instance configured for the given task type.

    task: "classification" | "extraction" | "similarity"
    """
    model = _MODELS.get(task, _MODELS["extraction"])
    return ChatGroq(model=model, temperature=0, api_key=os.environ["GROQ_API_KEY"])
