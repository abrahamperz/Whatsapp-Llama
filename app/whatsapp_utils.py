# app/whatsapp_utils.py
from twilio.rest import Client
import os
from app.logger_utils import logger

# Cargar variables de entorno
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

def respond(to_number, message: str = "", media_url: str = None) -> None:
    """Función para enviar un mensaje por WhatsApp utilizando Twilio"""
    logger.info(f"Intentando enviar mensaje a (antes de limpieza): {to_number}")
    try:
        to_number = to_number.replace("whatsapp:", "").lstrip("+")
        to_number = "".join(to_number.split())
        if not to_number.startswith("52"):
            to_number = f"52{to_number}"
        formatted_to_number = f"whatsapp:+{to_number}"

        TWILIO_WHATSAPP_PHONE_NUMBER = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

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
        raise Exception("No se pudo enviar el mensaje por WhatsApp")
