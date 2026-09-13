
"""
Cliente para comunicarnos con la API de TMDB.
"""

import requests
from config import TMDB_API_KEY


# URL base de la API de TMDB
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def search_movies(query: str, language: str = "es-MX") -> list[dict]:
    """
    Busca películas en TMDB a partir de un texto.

    Parameters
    ----------
    query : str
        Nombre o título de la película que queremos buscar.

    language : str
        Idioma en el que queremos recibir los resultados.

    Returns
    -------
    list[dict]
        Lista de películas encontradas.
    """

    # Endpoint de búsqueda de películas
    url = f"{TMDB_BASE_URL}/search/movie"

    # Parámetros enviados a TMDB
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": language,
        "include_adult": False,
    }

    # Realizamos la petición
    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    # Si TMDB devuelve un error HTTP, se genera una excepción.
    response.raise_for_status()

    # Convertimos la respuesta JSON a un diccionario de Python.
    data = response.json()

    # Devolvemos únicamente la lista de resultados.
    return data.get("results", [])


def get_movie_details(
    tmdb_id: int,
    language: str = "es-MX",
) -> dict:
    """
    Obtiene la información completa de una película.

    Parameters
    ----------
    tmdb_id : int
        Identificador de la película en TMDB.

    language : str
        Idioma de la respuesta.

    Returns
    -------
    dict
        Información detallada de la película.
    """

    # Endpoint para obtener los detalles de una película.
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"

    # Solicitamos también créditos y datos externos.
    params = {
        "api_key": TMDB_API_KEY,
        "language": language,
        "append_to_response": "credits,external_ids",
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def get_movie_director(
    tmdb_id: int,
) -> str | None:
    """
    Obtiene el director (o directores) de una película a partir de sus créditos en TMDB.

    Parameters
    ----------
    tmdb_id : int
        Identificador de la película en TMDB.

    Returns
    -------
    str | None
        Nombres de los directores separados por coma, o None si no se encontró.
    """
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits"
    params = {
        "api_key": TMDB_API_KEY,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        crew = response.json().get("crew", [])
        directors = []
        for person in crew:
            if person.get("job") == "Director":
                name = person.get("name")
                if name and name not in directors:
                    directors.append(name)
        return ", ".join(directors) if directors else None
    except Exception:
        return None