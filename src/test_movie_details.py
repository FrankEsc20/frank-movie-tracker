
"""
Prueba para obtener información detallada de una película.
"""

import sys
from pathlib import Path


# Permite importar módulos desde src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


from tmdb import get_movie_details


# ID de Interstellar en TMDB.
TMDB_ID = 157336


movie = get_movie_details(TMDB_ID)


print("Título:", movie.get("title"))
print("Título original:", movie.get("original_title"))
print("Fecha:", movie.get("release_date"))
print("Duración:", movie.get("runtime"))
print("Idioma:", movie.get("original_language"))
print("IMDb:", movie.get("external_ids", {}).get("imdb_id"))
print("Poster:", movie.get("poster_path"))
print("Director(es):")


# Revisamos los créditos para encontrar al director.
credits = movie.get("credits", {})

for person in credits.get("crew", []):
    if person.get("job") == "Director":
        print(f"  - {person.get('name')}")