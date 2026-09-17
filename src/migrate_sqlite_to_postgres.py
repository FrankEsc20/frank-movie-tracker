"""
Script para migrar todos los datos de SQLite a PostgreSQL.
"""

import os
import sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = BASE_DIR / "data" / "movies.db"


def get_postgres_connection():
    """Obtiene conexión a PostgreSQL usando variables de entorno."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def create_postgres_tables(pg_conn):
    """Crea las tablas en PostgreSQL si aún no existen."""
    with pg_conn.cursor() as cur:
        cur.execute(
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
    pg_conn.commit()


def migrate():
    """Lee datos de SQLite y los inserta en PostgreSQL."""
    if not SQLITE_PATH.exists():
        print(f"❌ No se encontró la base de datos SQLite en {SQLITE_PATH}")
        return

    print("🔌 Conectando a SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print("🔌 Conectando a PostgreSQL...")
    try:
        pg_conn = get_postgres_connection()
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        print("Verifica los datos en tu archivo .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD o DATABASE_URL)")
        return

    print("🛠️ Creando tablas en PostgreSQL...")
    create_postgres_tables(pg_conn)

    # 1. Migrar películas
    sqlite_cur.execute("SELECT * FROM movies ORDER BY id ASC")
    movies = sqlite_cur.fetchall()
    print(f"🎬 Encontradas {len(movies)} películas en SQLite...")

    with pg_conn.cursor() as pg_cur:
        for m in movies:
            pg_cur.execute(
                """
                INSERT INTO movies (
                    id, tmdb_id, imdb_id, title, original_title, release_date,
                    runtime, overview, tagline, original_language, poster_path,
                    backdrop_path, budget, revenue, director, genres, created_at, updated_at
                ) VALUES (
                    %(id)s, %(tmdb_id)s, %(imdb_id)s, %(title)s, %(original_title)s, %(release_date)s,
                    %(runtime)s, %(overview)s, %(tagline)s, %(original_language)s, %(poster_path)s,
                    %(backdrop_path)s, %(budget)s, %(revenue)s, %(director)s, %(genres)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (tmdb_id) DO NOTHING;
                """,
                dict(m),
            )

        # Ajustar la secuencia de autoincremento para movies
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('movies', 'id'), COALESCE(MAX(id), 1)) FROM movies;")

    pg_conn.commit()
    print(f"✅ {len(movies)} películas migradas exitosamente.")

    # 2. Migrar historial de visualizaciones
    sqlite_cur.execute("SELECT * FROM watch_history ORDER BY id ASC")
    watches = sqlite_cur.fetchall()
    print(f"👁️ Encontrados {len(watches)} registros de visualización en SQLite...")

    with pg_conn.cursor() as pg_cur:
        for w in watches:
            pg_cur.execute(
                """
                INSERT INTO watch_history (
                    id, movie_id, watched_at, rating, review, rewatch, created_at
                ) VALUES (
                    %(id)s, %(movie_id)s, %(watched_at)s, %(rating)s, %(review)s, %(rewatch)s, %(created_at)s
                )
                ON CONFLICT (id) DO NOTHING;
                """,
                dict(w),
            )

        # Ajustar la secuencia de autoincremento para watch_history
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('watch_history', 'id'), COALESCE(MAX(id), 1)) FROM watch_history;")

    pg_conn.commit()
    print(f"✅ {len(watches)} registros de visualización migrados exitosamente.")

    sqlite_conn.close()
    pg_conn.close()
    print("\n🎉 ¡Migración de SQLite a PostgreSQL completada con éxito!")


if __name__ == "__main__":
    migrate()
