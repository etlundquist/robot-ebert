import json
import pytest

from sqlalchemy import select
from datetime import datetime

from app.models import Movie


@pytest.fixture(autouse=True)
def patch_constant(monkeypatch, test_engine):
    """mock the CloudSQL SQLAlchemy Engine with a local DuckDB Engine for testing"""

    monkeypatch.setattr("app.api.movies.ENGINE", test_engine)


@pytest.fixture(scope="module")
def movie():
    """sample movie for testing"""

    movie = Movie(
        tmdb_id="test",
        title="test title",
        release_date=datetime(2000, 1, 1),
        runtime=90.0,
        genres=["test genre 1", "test genre 2"],
        keywords=["test keyword 1", "test keyword 2"],
        overview="test overview",
        budget=100,
        revenue=100,
        popularity=10.0,
        vote_average=5.0,
        vote_count=100
    )
    return movie


def test_create_movie(client, movie):
    """unit test: create_movie()"""

    response = client.post("/movies/", json=json.loads(movie.model_dump_json()))
    assert response.status_code == 200
    assert response.json() == movie.tmdb_id


def test_get_movie(client, movie):
    """unit test: get_movie()"""

    response = client.get(f"/movies/{movie.tmdb_id}/")
    assert response.status_code == 200
    assert Movie(**response.json()) == movie


# FIXME: updates to columns part of an index are handled as deletions/insertions which causes unexpected constraint violations
# FIXME: https://duckdb.org/docs/sql/indexes.html#over-eager-unique-constraint-checking
# def test_update_movie(client, movie):
#     """unit test: update_movie()"""

#     movie.title = "test title 2"
#     movie.overview = "test overview 2"
#     response = client.put(f"/movies/{movie.tmdb_id}/", json=json.loads(movie.model_dump_json()))
#     assert response.status_code == 200


def test_delete_movie(client, movie):
    """unit test: delete_movie()"""

    response = client.delete(f"/movies/{movie.tmdb_id}/")
    assert response.status_code == 200
