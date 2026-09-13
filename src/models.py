
"""
Modelos de datos utilizados por el proyecto.
"""

from datetime import date
from pydantic import BaseModel


class Movie(BaseModel):
    """
    Representa una película en nuestra biblioteca.
    """

    id: int | None = None
    tmdb_id: int
    imdb_id: str | None = None
    title: str
    original_title: str | None = None
    release_date: date | None = None
    runtime: int | None = None
    overview: str | None = None
    tagline: str | None = None
    original_language: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    budget: int | None = None
    revenue: int | None = None
    director: str | None = None
    genres: str | None = None

    @classmethod
    def from_tmdb(cls, data: dict) -> "Movie":
        """
        Crea una instancia de Movie a partir del diccionario devuelto por TMDB.
        Limpia y adapta los datos según nuestro esquema.
        """
        # IMDb ID puede venir en la raíz o dentro de external_ids
        imdb_id = data.get("imdb_id") or (data.get("external_ids") or {}).get("imdb_id")

        # Evita que cadenas vacías rompan la validación de fecha
        release_date = data.get("release_date") or None

        # Extrae el nombre del director (o directores) desde los créditos
        crew = (data.get("credits") or {}).get("crew", [])
        directors = []
        for person in crew:
            if person.get("job") == "Director":
                name = person.get("name")
                if name and name not in directors:
                    directors.append(name)
        director_str = ", ".join(directors) if directors else None

        # Extrae los nombres de los géneros
        genres_list = [g["name"] for g in (data.get("genres") or []) if "name" in g]
        genres_str = ", ".join(genres_list) if genres_list else None

        return cls(
            tmdb_id=data["id"],
            imdb_id=imdb_id,
            title=data.get("title", ""),
            original_title=data.get("original_title"),
            release_date=release_date,
            runtime=data.get("runtime"),
            overview=data.get("overview") or None,
            tagline=data.get("tagline") or None,
            original_language=data.get("original_language"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            budget=data.get("budget") or None,
            revenue=data.get("revenue") or None,
            director=director_str,
            genres=genres_str,
        )


class WatchHistory(BaseModel):
    """
    Representa un registro de visualización de una película.
    """

    id: int | None = None
    movie_id: int
    watched_at: date
    rating: float
    review: str | None = None
    rewatch: int = 0
