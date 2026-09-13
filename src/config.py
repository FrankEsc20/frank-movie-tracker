"""
Configuración general del proyecto.

Aquí cargamos las variables definidas en el archivo .env
para evitar escribir credenciales directamente en el código.
"""

import os

from dotenv import load_dotenv


# Carga las variables del archivo .env
load_dotenv()


# API key de TMDB
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Token del bot de Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# Validamos que existan las credenciales necesarias antes de ejecutar
if not TMDB_API_KEY:
    raise ValueError(
        "No se encontró TMDB_API_KEY. "
        "Verifica que exista en el archivo .env."
    )

if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "No se encontró TELEGRAM_BOT_TOKEN. "
        "Verifica que exista en el archivo .env."
    )
