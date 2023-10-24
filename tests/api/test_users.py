import pytest
from sqlalchemy import select
from uuid import UUID

from app import database
from app.models import User, UserRequest


@pytest.fixture(autouse=True)
def patch_constant(monkeypatch, test_engine):
    """mock the CloudSQL SQLAlchemy Engine with a local DuckDB Engine for testing"""

    monkeypatch.setattr("app.api.users.ENGINE", test_engine)


def test_create_user(client):
    """unit test: create_user()"""

    user_request = UserRequest(fname="test", lname="test", email="test@test.com")
    response = client.post("/users/", json=user_request.model_dump())

    try:
        UUID(response.json())
        uuid_response = True
    except ValueError:
        uuid_response = False

    assert response.status_code == 200
    assert uuid_response


def test_get_user(client, test_engine):
    """unit test: get_user()"""

    with test_engine.begin() as cnx:
        statement = select(database.users).limit(1)
        user_id = cnx.execute(statement).one()._asdict()['user_id']

    response = client.get(f"/users/{user_id}/")
    expected = User(user_id=user_id, fname="test", lname="test", email="test@test.com")
    result = User(**response.json())

    assert response.status_code == 200
    assert expected == result


def test_update_user(client, test_engine):
    """unit test: update_user()"""

    with test_engine.begin() as cnx:
        statement = select(database.users).limit(1)
        user_id = cnx.execute(statement).one()._asdict()['user_id']

    user_request = UserRequest(fname="test2", lname="test2", email="test2@test2.com")
    response = client.put(f"/users/{user_id}/", json=user_request.model_dump())
    assert response.status_code == 200


def test_delete_user(client, test_engine):
    """unit test: delete_user()"""

    with test_engine.begin() as cnx:
        statement = select(database.users).limit(1)
        user_id = cnx.execute(statement).one()._asdict()['user_id']

    response = client.delete(f"/users/{user_id}/")
    assert response.status_code == 200
