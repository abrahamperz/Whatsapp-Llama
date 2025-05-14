# app/main.py
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from fastapi import Form, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.whatsapp_utils import respond  # Importamos respond desde whatsapp_utils.py
from app.openai_utils import gpt_without_functions, summarise_conversation
from app.redis_utils import redis_conn
from app.logger_utils import logger
from app.cookies_utils import set_cookies, get_cookies
from app.prompts import SYSTEM_PROMPT
# Cargar variables de entorno
load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Configuración de FastAPI
app = FastAPI(
    title="Twilio-OpenAI-WhatsApp-Bot",
    description="Twilio OpenAI WhatsApp Bot",
    version="0.0.1",
    contact={
        "name": "Lena Shakurova",
        "url": "http://shakurova.io/",
        "email": "lena@shakurova.io",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Endpoint principal de WhatsApp
@app.post('/whatsapp-endpoint')
async def whatsapp_endpoint(request: Request, From: str = Form(...), Body: str = Form(...)):
    logger.info(f'WhatsApp endpoint triggered...')
    logger.info(f'Request: {request}')
    logger.info(f'Body: {Body}')
    logger.info(f'From: {From}')

    query = Body
    phone_no = From.replace('whatsapp:', '')
    chat_session_id = phone_no

    history = get_cookies(redis_conn, f'whatsapp_twilio_demo_{chat_session_id}_history') or []
    if history:
        history = json.loads(history)

    history.append({"role": 'user', "content": query})

    # Resumen de conversación
    history_summary = summarise_conversation(history)

    # Prompt del sistema
    system_prompt = SYSTEM_PROMPT.format(
        history_summary=history_summary,
        today=datetime.now().date()
    )

    # Procesar respuesta con OpenAI
    try:
        openai_response = gpt_without_functions(
            model=MODEL_NAME,
            stream=False,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'assistant', 'content': "Hi there, how can I help you?"}
            ] + history
        )
        logger.info(f"OpenAI response: {openai_response}")
        chatbot_response = openai_response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error procesando la respuesta de OpenAI: {e}")
        chatbot_response = "Lo siento, ocurrió un error al generar la respuesta. Estamos trabajando en ello. Gracias por su paciencia."

        # ✅ Enviar alerta a administrador
        try:
            # Enviar mensaje de alerta a tu número personal
            respond(
               to_number="+523411557781",
               message=f"[ALERTA] Se produjo un error técnico al procesar un mensaje de WhatsApp de {From}. Error: {str(e)}"
            )
            logger.info("Alerta de error técnico enviada al número personal.")
        except Exception as alert_error:
             logger.error(f"No se pudo enviar la alerta al administrador: {alert_error}")

    # Guardar historial actualizado
    history.append({'role': 'assistant', 'content': chatbot_response})
    set_cookies(redis_conn, name=f'whatsapp_twilio_demo_{chat_session_id}_history', value=json.dumps(history))

    # Enviar imagen si se solicita
    if any(word in query.lower() for word in ["foto", "imagen", "ver el departamento", "tienes foto", "puedo ver"]):
        respond(
            From,
            message="Aquí tienes una imagen del departamento.",
            media_url="https://i.imgur.com/aXSatsv.jpeg"
        )
    else:
        respond(From, chatbot_response)

    return {"status": "ok", "message": chatbot_response}

# Ejecutar con Uvicorn
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app.main:app", host='0.0.0.0', port=3002, reload=True)
