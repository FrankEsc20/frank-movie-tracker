
"""
Prueba básica de conexión con TMDB.
"""

import sys
from pathlib import Path


# Permite importar módulos ubicados dentro de src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


from tmdb import search_movies


# Buscamos una película conocida.
results = search_movies("Interstellar")


print(f"Resultados encontrados: {len(results)}")

for movie in results[:5]:
    print(
        f"{movie.get('id')} | "
        f"{movie.get('title')} | "
        f"{movie.get('release_date')}"
    )