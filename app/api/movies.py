from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import insert, select, update, delete

from app import database
from app.models import Movie
from app.constants import engine

router = APIRouter()


@router.post("/movies/", status_code=200)
def create_movie(movie: Movie) -> str:
    """create a new movie"""

    with engine.begin() as cnx:
        statement = insert(
            database.movies
        ).values(
            updated_at=datetime.now(),
            **movie.model_dump()
        )
        cnx.execute(statement)
        return movie.tmdb_id


@router.get("/movies/{tmdb_id}/", status_code=200)
def get_movie(tmdb_id: str) -> Movie:
    """get an existing movie by ID"""

    with engine.begin() as cnx:
        statement = select(
            database.movies
        ).where(
            database.movies.c.tmdb_id == tmdb_id
        )
        movie = Movie(**cnx.execute(statement).one()._asdict())
        return movie


@router.put("/movies/{tmdb_id}/", status_code=200)
def update_movie(tmdb_id: str, movie: Movie) -> None:
    """update an existing movie by ID"""

    movie_data = movie.model_dump()
    del movie_data["tmdb_id"]

    with engine.begin() as cnx:
        statement = update(
            database.movies
        ).where(
            database.movies.c.tmdb_id == tmdb_id
        ).values(
            updated_at=datetime.now(),
            **movie_data
        )
        cnx.execute(statement)


@router.delete("/movies/{tmdb_id}/", status_code=200)
def delete_movie(tmdb_id: str) -> None:
    """delete an existing movie by ID"""

    with engine.begin() as cnx:
        statement = delete(
            database.movies
        ).where(
            database.movies.c.tmdb_id == tmdb_id
        )
        cnx.execute(statement)
