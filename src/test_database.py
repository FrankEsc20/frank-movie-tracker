"""
Prueba del flujo TMDB -> Movie -> SQLite.
"""

import sys
from pathlib import Path

# Permite importar módulos desde src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from database import get_all_movies, get_movie_by_tmdb_id, save_movie
from models import Movie
from tmdb import get_movie_details


print("1. Obteniendo información desde TMDB...")
raw_data = get_movie_details(157336)

print("2. Transformando a modelo Movie...")
movie = Movie.from_tmdb(raw_data)
print(f"   Película lista: {movie.title} (TMDB ID: {movie.tmdb_id})")

print("3. Guardando en SQLite...")
saved_movie = save_movie(movie)
print(f"   Película guardada con ID local: {saved_movie.id}")

print("4. Probando que no se duplique al re-guardar...")
duplicate_test = save_movie(movie)
print(f"   ID retornado al intentar re-guardar: {duplicate_test.id}")

print("5. Consultando desde SQLite por TMDB ID...")
loaded_movie = get_movie_by_tmdb_id(157336)
if loaded_movie:
    print(f"   Recuperada con éxito:")
    print(f"     ID local: {loaded_movie.id}")
    print(f"     Título:   {loaded_movie.title}")
    print(f"     Director: {loaded_movie.director}")
    print(f"     Géneros:  {loaded_movie.genres}")

print("6. Total de películas en la base de datos:")
all_movies = get_all_movies()
print(f"   Total: {len(all_movies)}")
