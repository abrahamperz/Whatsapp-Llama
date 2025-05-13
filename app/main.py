import os
import json
from datetime import datetime
from dotenv import load_dotenv

from fastapi import Form, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from twilio.rest import Client

from app.cookies_utils import set_cookies, get_cookies, clear_cookies
from app.prompts import SYSTEM_PROMPT
from app.openai_utils import gpt_without_functions, summarise_conversation
from app.redis_utils import redis_conn
from app.logger_utils import logger

# Load environment variables from a .env file
load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

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


def respond(to_number, message: str = "", media_url: str = None) -> None:
    logger.info(f"Intentando enviar mensaje a (antes de limpieza): {to_number}")
    try:
        to_number = to_number.replace("whatsapp:", "").lstrip("+")
        to_number = "".join(to_number.split())
        if not to_number.startswith("52"):
            to_number = f"52{to_number}"
        formatted_to_number = f"whatsapp:+{to_number}"

        TWILIO_WHATSAPP_PHONE_NUMBER = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Armado del mensaje
        message_data = {
            "from_": TWILIO_WHATSAPP_PHONE_NUMBER,
            "to": formatted_to_number
        }

        if media_url:
            message_data["media_url"] = [media_url]
            if message:
                message_data["body"] = message
        else:
            message_data["body"] = message

        twilio_client.messages.create(**message_data)
        logger.info(f"Mensaje enviado a {formatted_to_number}")
    except Exception as e:
        logger.error(f"Error enviando mensaje con Twilio: {e}")
        raise HTTPException(status_code=500, detail="No se pudo enviar el mensaje por WhatsApp")

@app.post('/whatsapp-endpoint')
async def whatsapp_endpoint(request: Request, From: str = Form(...), Body: str = Form(...)):
    logger.info(f'WhatsApp endpoint triggered...')
    logger.info(f'Request: {request}')
    logger.info(f'Body: {Body}')
    logger.info(f'From: {From}')

    query = Body
    phone_no = From.replace('whatsapp:', '')
    chat_session_id = phone_no

    # Retrieve chat history from Redis
    history = get_cookies(redis_conn, f'whatsapp_twilio_demo_{chat_session_id}_history') or []
    if history:
        history = json.loads(history)

    # Append the user's query to the chat history
    history.append({"role": 'user', "content": query})

    # Summarize the conversation history
    history_summary = summarise_conversation(history)

    # Format the system prompt with the conversation summary and current date
    system_prompt = SYSTEM_PROMPT.format(
        history_summary=history_summary,
        today=datetime.now().date()
    )

    # Get a response from OpenAI's GPT model
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
        chatbot_response = "Lo siento, ocurrió un error al generar la respuesta."

    # Guardar el nuevo mensaje en el historial
    history.append({'role': 'assistant', 'content': chatbot_response})
    set_cookies(redis_conn, name=f'whatsapp_twilio_demo_{chat_session_id}_history', value=json.dumps(history))

    # ✅ Verificar si el usuario pidió una imagen
    if any(word in query.lower() for word in ["foto", "imagen", "ver el departamento", "tienes foto", "puedo ver"]):
        respond(
            From,
            message="Aquí tienes una imagen del departamento.",
            media_url="https://i.imgur.com/aXSatsv.jpeg"
        )
    else:
        respond(From, chatbot_response)

    return {"status": "ok", "message": chatbot_response}



if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app.main:app", host='0.0.0.0', port=3002, reload=True)
