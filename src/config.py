
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


# Validamos que exista la API key antes de ejecutar el proyecto.
if not TMDB_API_KEY:
    raise ValueError(
        "No se encontró TMDB_API_KEY. "
        "Verifica que exista en el archivo .env."
    )