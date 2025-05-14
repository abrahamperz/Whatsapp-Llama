# app/openai_utils.py
import os
from dotenv import load_dotenv
from litellm import completion
from app.prompts import SUMMARY_PROMPT

# Carga las variables de entorno
load_dotenv()

# Configuración de modelos y llaves
MODEL_NAME = os.getenv("LLM_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EXTERNAL_MODEL = os.getenv("EXTERNAL_MODEL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configura las llaves como variables de entorno
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Parámetros del modelo
TEMPERATURE = 0.1
MAX_TOKENS = 350
STOP_SEQUENCES = ["==="]
TOP_P = 1
TOP_K = 1
BEST_OF = 1
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0

# Modelos soportados
SUPPORTED_MODELS = {
    "groq/llama3-70b-8192",
    "groq/llama-3.1-8b-instant",
    "groq/llama-3.1-70b-versatile",
    "gpt-3.5-turbo-0125",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-0125-preview",
    "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
    "bedrock/anthropic.claude-3-opus-20240229-v1:0",
    "bedrock/anthropic.claude-v2:1",
}

def gpt_without_functions(model, stream=False, messages=[]):
    """GPT model without function call."""
    try:
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Modelo no soportado: {model}")
        response = completion(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=TOP_P,
            stream=stream
        )
        return response
    except Exception as e:
        print(f"Error en gpt_without_functions: {e}")
        return {
            "choices": [{
                "message": {
                    "content": "Hubo un problema técnico. Estamos trabajando en resolverlo. Gracias por su paciencia."
                }
            }]
        }

def summarise_conversation(history):
    """Resumir el historial de conversación en una sola frase."""
    try:
        conversation = ""
        for item in history[-70:]:
            if 'user_input' in item:
                conversation += f"User: {item['user_input']}\n"
            if 'bot_response' in item:
                conversation += f"Bot: {item['bot_response']}\n"

        openai_response = gpt_without_functions(
            model=MODEL_NAME,
            stream=False,
            messages=[
                {'role': 'system', 'content': SUMMARY_PROMPT},
                {'role': 'user', 'content': conversation}
            ]
        )

        chatbot_response = openai_response["choices"][0]["message"]["content"].strip()
        return chatbot_response
    except Exception as e:
        print(f"Error en summarise_conversation: {e}")
        return "Hubo un problema al resumir la conversación. Estamos trabajando en resolverlo. Gracias por su paciencia."
