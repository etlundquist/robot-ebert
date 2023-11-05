import pytest

from datetime import datetime
from sqlalchemy import insert

from src.backend.app import database
from src.shared.models import Movie
from src.backend.app.lib import get_movies


@pytest.fixture(autouse=True)
def patch_constant(monkeypatch, test_engine):
    """mock the CloudSQL SQLAlchemy Engine with a local DuckDB Engine for testing"""

    monkeypatch.setattr("app.lib.utils.engine", test_engine)


@pytest.fixture(scope="module")
def movies(test_engine):
    """sample movies for testing"""

    movies = [
        Movie(
            tmdb_id="1",
            tmdb_homepage="https://www.themoviedb.org/movie/1",
            title="test title 1",
            language="en",
            release_date=datetime(2000, 1, 1),
            runtime=90,
            director="test director",
            actors=["test actor 1", "test actor 2"],
            genres=["test genre 1", "test genre 2"],
            keywords=["test keyword 1", "test keyword 2"],
            overview="test overview",
            budget=100,
            revenue=100,
            popularity=10.0,
            vote_average=5.0,
            vote_count=100
        ),
        Movie(
            tmdb_id="2",
            tmdb_homepage="https://www.themoviedb.org/movie/2",
            title="test title 2",
            language="en",
            release_date=datetime(2000, 1, 1),
            runtime=90,
            director="test director",
            actors=["test actor 1", "test actor 2"],
            genres=["test genre 1", "test genre 2"],
            keywords=["test keyword 1", "test keyword 2"],
            overview="test overview",
            budget=100,
            revenue=100,
            popularity=10.0,
            vote_average=5.0,
            vote_count=100
        )
    ]

    with test_engine.begin() as cnx:
        for movie in movies:
            cnx.execute(insert(database.movies).values(updated_at=datetime.now(), **movie.model_dump()))

    return movies


def test_get_movies(movies):
    """unit test: get_movies()"""

    response = get_movies(tmdb_ids=[movie.tmdb_id for movie in movies])
    assert response == movies
