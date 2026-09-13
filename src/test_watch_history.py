"""
Prueba del registro y consulta de visualizaciones (watch_history).
"""

import sys
from datetime import date
from pathlib import Path

# Permite importar módulos desde src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from database import (
    get_all_movies,
    get_movie_by_tmdb_id,
    get_recent_watches,
    get_watch_history_for_movie,
    save_movie,
    save_watch_history,
)
from models import Movie, WatchHistory
from tmdb import get_movie_details


# 1. Aseguramos que la película exista en la base de datos
movie = get_movie_by_tmdb_id(157336)
if not movie:
    print("Obteniendo y guardando Interestelar...")
    raw_data = get_movie_details(157336)
    movie = save_movie(Movie.from_tmdb(raw_data))

print(f"Película en base de datos: {movie.title} (ID local: {movie.id})")

# 2. Registramos la primera visualización
print("\nRegistrando primera visualización...")
watch1 = WatchHistory(
    movie_id=movie.id,
    watched_at=date(2026, 9, 12),
    rating=9.5,
    review="Obra maestra del cine de ciencia ficción.",
    rewatch=0,
)
saved_watch1 = save_watch_history(watch1)
print(f"  Guardada con ID: {saved_watch1.id} | Rating: {saved_watch1.rating} | Rewatch: {saved_watch1.rewatch}")

# 3. Registramos una segunda visualización (Rewatch)
print("\nRegistrando segunda visualización (Rewatch)...")
watch2 = WatchHistory(
    movie_id=movie.id,
    watched_at=date(2027, 12, 20),
    rating=10.0,
    review="Aún mejor la segunda vez en pantalla gigante.",
    rewatch=1,
)
saved_watch2 = save_watch_history(watch2)
print(f"  Guardada con ID: {saved_watch2.id} | Rating: {saved_watch2.rating} | Rewatch: {saved_watch2.rewatch}")

# 4. Verificamos que la película sigue siendo 1 sola en la tabla movies
total_movies = len(get_all_movies())
print(f"\nTotal de películas en biblioteca (debe ser 1): {total_movies}")

# 5. Verificamos el historial de esta película
history = get_watch_history_for_movie(movie.id)
print(f"Total de visualizaciones de '{movie.title}': {len(history)}")

# 6. Probamos la consulta de visualizaciones recientes (para el futuro /recent de Telegram)
print("\n--- Visualizaciones recientes (simulando comando /recent) ---")
recent = get_recent_watches(limit=5)
for item in recent:
    rewatch_str = "Sí" if item["rewatch"] == 1 else "No"
    print(f"🎬 {item['title']} ({item['release_date'][:4] if item['release_date'] else 'N/A'})")
    print(f"   Director: {item['director']}")
    print(f"   Vista el: {item['watched_at']} | Calificación: {item['rating']}/10 | Rewatch: {rewatch_str}")
    print(f"   Reseña:   \"{item['review']}\"\n")
