
"""
Gestión de la base de datos SQLite.
"""

import sqlite3
from pathlib import Path


# Directorio donde se almacenará la base de datos.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Ruta completa de la base de datos.
DATABASE_PATH = DATA_DIR / "movies.db"


def get_connection() -> sqlite3.Connection:
    """
    Crea y devuelve una conexión a SQLite.
    """

    # Crea el directorio data/ si todavía no existe.
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    # Permite acceder a las columnas por nombre además de índice.
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """
    Crea las tablas necesarias si todavía no existen.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # Tabla principal de películas.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tmdb_id INTEGER NOT NULL UNIQUE,
            imdb_id TEXT,
            title TEXT NOT NULL,
            original_title TEXT,
            release_date TEXT,
            runtime INTEGER,
            overview TEXT,
            tagline TEXT,
            original_language TEXT,
            poster_path TEXT,
            backdrop_path TEXT,
            budget INTEGER,
            revenue INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Historial de visualizaciones.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            watched_at TEXT NOT NULL,
            rating REAL NOT NULL,
            review TEXT,
            rewatch INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (movie_id)
                REFERENCES movies(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()