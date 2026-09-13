"""
Prueba de validación de los modelos y la transformación desde TMDB.
"""

import sys
from datetime import date
from pathlib import Path

# Permite importar módulos desde src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from models import Movie, WatchHistory
from tmdb import get_movie_details


# 1. Probamos la transformación desde TMDB usando Interstellar (157336)
print("--- Probando Movie.from_tmdb ---")
raw_data = get_movie_details(157336)
movie = Movie.from_tmdb(raw_data)

print("Película creada exitosamente:")
print(f"  TMDB ID:         {movie.tmdb_id}")
print(f"  Título:          {movie.title}")
print(f"  Título original: {movie.original_title}")
print(f"  Director:        {movie.director}")
print(f"  Géneros:         {movie.genres}")
print(f"  Fecha estreno:   {movie.release_date} (tipo: {type(movie.release_date).__name__})")
print(f"  Duración:        {movie.runtime} min")
print(f"  IMDb ID:         {movie.imdb_id}")

# 2. Probamos el modelo WatchHistory
print("\n--- Probando WatchHistory ---")
watch = WatchHistory(
    movie_id=1,
    watched_at=date(2026, 9, 12),
    rating=9.5,
    review="Obra maestra del cine de ciencia ficción.",
    rewatch=0,
)

print("Registro de visualización creado exitosamente:")
print(f"  Movie ID:        {watch.movie_id}")
print(f"  Fecha:           {watch.watched_at}")
print(f"  Rating:          {watch.rating}")
print(f"  Review:          {watch.review}")
print(f"  Rewatch:         {watch.rewatch}")
