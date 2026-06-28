import os

from langchain_groq import ChatGroq

MODEL_EXTRACCION = "llama-3.3-70b-versatile"


def get_groq_model() -> ChatGroq:
    return ChatGroq(model=MODEL_EXTRACCION, temperature=0, api_key=os.environ["GROQ_API_KEY"])
