
"""
Modelos de datos utilizados por el proyecto.
"""

from datetime import date
from pydantic import BaseModel, Field


class Movie(BaseModel):
    """
    Representa una película almacenada en nuestra biblioteca.
    """

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