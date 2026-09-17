"""
Gestión de la base de datos PostgreSQL (alojada en CasaOS / Ubuntu).
"""

from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

from config import (
    DATABASE_URL,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)
from models import Movie, WatchHistory


def get_connection():
    """
    Crea y devuelve una conexión a la base de datos PostgreSQL.
    Utiliza RealDictCursor para que los resultados se comporten como diccionarios.
    """
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def initialize_database() -> None:
    """
    Crea las tablas necesarias en PostgreSQL si todavía no existen.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Tabla principal de películas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            tmdb_id INTEGER NOT NULL UNIQUE,
            imdb_id TEXT,
            title TEXT NOT NULL,
            original_title TEXT,
            release_date DATE,
            runtime INTEGER,
            overview TEXT,
            tagline TEXT,
            original_language TEXT,
            poster_path TEXT,
            backdrop_path TEXT,
            budget BIGINT,
            revenue BIGINT,
            director TEXT,
            genres TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Historial de visualizaciones
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_history (
            id SERIAL PRIMARY KEY,
            movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            watched_at DATE NOT NULL,
            rating NUMERIC(3, 1) NOT NULL,
            review TEXT,
            rewatch INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    connection.commit()
    cursor.close()
    connection.close()


def save_movie(movie: Movie) -> Movie:
    """
    Guarda una película en la base de datos.
    Si ya existe (por tmdb_id), devuelve la existente para no duplicar.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Verificamos si ya existe
    cursor.execute("SELECT * FROM movies WHERE tmdb_id = %s", (movie.tmdb_id,))
    row = cursor.fetchone()

    if row:
        cursor.close()
        connection.close()
        return Movie(**dict(row))

    # Inserción de nueva película con RETURNING id
    cursor.execute(
        """
        INSERT INTO movies (
            tmdb_id,
            imdb_id,
            title,
            original_title,
            release_date,
            runtime,
            overview,
            tagline,
            original_language,
            poster_path,
            backdrop_path,
            budget,
            revenue,
            director,
            genres
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            movie.tmdb_id,
            movie.imdb_id,
            movie.title,
            movie.original_title,
            movie.release_date,
            movie.runtime,
            movie.overview,
            movie.tagline,
            movie.original_language,
            movie.poster_path,
            movie.backdrop_path,
            movie.budget,
            movie.revenue,
            movie.director,
            movie.genres,
        ),
    )

    result = cursor.fetchone()
    movie.id = result["id"]
    connection.commit()
    cursor.close()
    connection.close()

    return movie


def get_movie_by_tmdb_id(tmdb_id: int) -> Movie | None:
    """
    Busca una película por su identificador de TMDB.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM movies WHERE tmdb_id = %s", (tmdb_id,))
    row = cursor.fetchone()
    cursor.close()
    connection.close()

    if row:
        return Movie(**dict(row))
    return None


def get_movie_by_id(movie_id: int) -> Movie | None:
    """
    Busca una película por su ID primario en la base de datos.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    row = cursor.fetchone()
    cursor.close()
    connection.close()

    if row:
        return Movie(**dict(row))
    return None


def get_all_movies() -> list[Movie]:
    """
    Devuelve todas las películas almacenadas en la base de datos ordenadas por título.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM movies ORDER BY title ASC")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return [Movie(**dict(row)) for row in rows]


def save_watch_history(watch: WatchHistory) -> WatchHistory:
    """
    Guarda un registro de visualización en la base de datos.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO watch_history (
            movie_id,
            watched_at,
            rating,
            review,
            rewatch
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            watch.movie_id,
            watch.watched_at,
            watch.rating,
            watch.review,
            watch.rewatch,
        ),
    )

    result = cursor.fetchone()
    watch.id = result["id"]
    connection.commit()
    cursor.close()
    connection.close()

    return watch


def get_watch_history_for_movie(movie_id: int) -> list[WatchHistory]:
    """
    Devuelve todo el historial de visualizaciones de una película en particular.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM watch_history
        WHERE movie_id = %s
        ORDER BY watched_at DESC, id DESC
        """,
        (movie_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return [WatchHistory(**dict(row)) for row in rows]


def get_recent_watches(limit: int = 10) -> list[dict]:
    """
    Devuelve las visualizaciones más recientes ordenadas por fecha de visualización
    (de más reciente a más antigua) junto con la información de la película.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            w.id AS watch_id,
            w.watched_at,
            w.rating,
            w.review,
            w.rewatch,
            m.id AS movie_id,
            m.tmdb_id,
            m.title,
            m.original_title,
            m.release_date,
            m.poster_path,
            m.director
        FROM watch_history w
        JOIN movies m ON w.movie_id = m.id
        ORDER BY w.watched_at DESC, w.id DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return [dict(row) for row in rows]


def get_watch_by_id(watch_id: int) -> dict | None:
    """
    Obtiene todos los datos de un registro de visualización específico
    junto con la información de la película asociada.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            w.id AS watch_id,
            w.watched_at,
            w.rating,
            w.review,
            w.rewatch,
            w.created_at AS watch_created_at,
            m.id AS movie_id,
            m.tmdb_id,
            m.title,
            m.original_title,
            m.release_date,
            m.poster_path,
            m.director,
            m.genres
        FROM watch_history w
        JOIN movies m ON w.movie_id = m.id
        WHERE w.id = %s
        """,
        (watch_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    connection.close()

    if row:
        return dict(row)
    return None


def delete_watch_by_id(watch_id: int) -> bool:
    """
    Elimina un registro de visualización por su ID.
    Devuelve True si se eliminó, False si no existía.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM watch_history WHERE id = %s", (watch_id,))
    deleted = cursor.rowcount > 0

    connection.commit()
    cursor.close()
    connection.close()

    return deleted


def update_watch_history(
    watch_id: int,
    watched_at: date | str | None = None,
    rating: float | None = None,
    review: str | None = None,
    rewatch: int | None = None,
    clear_review: bool = False,
) -> bool:
    """
    Actualiza campos específicos de un registro de visualización.
    """
    updates = []
    params = []

    if watched_at is not None:
        updates.append("watched_at = %s")
        params.append(watched_at)

    if rating is not None:
        updates.append("rating = %s")
        params.append(rating)

    if clear_review:
        updates.append("review = NULL")
    elif review is not None:
        updates.append("review = %s")
        params.append(review)

    if rewatch is not None:
        updates.append("rewatch = %s")
        params.append(rewatch)

    if not updates:
        return False

    params.append(watch_id)

    connection = get_connection()
    cursor = connection.cursor()

    sql = f"UPDATE watch_history SET {', '.join(updates)} WHERE id = %s"
    cursor.execute(sql, tuple(params))
    updated = cursor.rowcount > 0

    connection.commit()
    cursor.close()
    connection.close()

    return updated


def search_watches_by_title(query: str, limit: int = 10) -> list[dict]:
    """
    Busca en el historial de visualizaciones por coincidencia en el título de la película.
    Utiliza ILIKE para búsqueda insensible a mayúsculas y minúsculas.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            w.id AS watch_id,
            w.watched_at,
            w.rating,
            w.review,
            w.rewatch,
            m.id AS movie_id,
            m.tmdb_id,
            m.title,
            m.original_title,
            m.release_date,
            m.poster_path,
            m.director
        FROM watch_history w
        JOIN movies m ON w.movie_id = m.id
        WHERE m.title ILIKE %s OR m.original_title ILIKE %s
        ORDER BY w.watched_at DESC, w.id DESC
        LIMIT %s
        """,
        (f"%{query}%", f"%{query}%", limit),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return [dict(row) for row in rows]
