
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import insert, select, update, delete

from app import database
from app.models import User, UserRequest
from app.constants import ENGINE

router = APIRouter()


@router.post("/users/", status_code=200)
def create_user(user_request: UserRequest) -> str:
    """create a new user"""

    with ENGINE.begin() as cnx:

        statement = select(
            database.users
        ).where(
            database.users.c.fname == user_request.fname,
            database.users.c.lname == user_request.lname,
            database.users.c.email == user_request.email
        )

        result = cnx.execute(statement).all()
        if result:
            raise ValueError(f"a user with fname={user_request.fname} lname={user_request.lname} email={user_request.email} already exists!")

        user_id = str(uuid4())
        statement = insert(
            database.users
        ).values(
            user_id=user_id,
            updated_at=datetime.now(),
            **user_request.model_dump()
        )

        cnx.execute(statement)
        return user_id


@router.get("/users/{user_id}/", status_code=200)
def get_user(user_id: str) -> User:
    """get an existing user by ID"""

    with ENGINE.begin() as cnx:
        statement = select(
            database.users
        ).where(
            database.users.c.user_id == user_id
        )
        user = User(**cnx.execute(statement).one()._asdict())
        return user


@router.put("/users/{user_id}/", status_code=200)
def update_user(user_id: str, user_request: UserRequest) -> None:
    """update an existing user by ID"""

    with ENGINE.begin() as cnx:
        statement = update(
            database.users
        ).where(
            database.users.c.user_id == user_id
        ).values(
            updated_at=datetime.now(),
            **user_request.model_dump()
        )
        cnx.execute(statement)


@router.delete("/users/{user_id}/", status_code=200)
def delete_user(user_id: str) -> None:
    """delete an existing user by ID"""

    with ENGINE.begin() as cnx:
        statement = delete(
            database.users
        ).where(
            database.users.c.user_id == user_id
        )
        cnx.execute(statement)
