
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import insert, select, update, delete
from passlib.context import CryptContext

from app import database
from app.models import NewUserRequest, UpdateUserRequest, DBUser
from app.constants import ENGINE

router = APIRouter()
password_context = CryptContext(schemes=["bcrypt"])


@router.post("/users/", status_code=200)
def create_user(user_request: NewUserRequest) -> str:
    """create a new user"""

    with ENGINE.begin() as cnx:

        # check to make sure there's not already an existing user with the same email
        statement = select(database.users).where(database.users.c.email == user_request.email)
        result = cnx.execute(statement).all()
        if result:
            raise ValueError(f"a user with email={user_request.email} already exists!")

        # generate a random user_id and hash the user's password for storage
        user_id = str(uuid4())
        hashed_password = password_context.hash(user_request.password)

        # insert a new user record into the database
        statement = insert(
            database.users
        ).values(
            user_id=user_id,
            email=user_request.email,
            hashed_password=hashed_password,
            fname=user_request.fname,
            lname=user_request.lname,
            updated_at=datetime.now()
        )

        cnx.execute(statement)
        return user_id


@router.get("/users/{user_id}/", status_code=200)
def get_user(user_id: str) -> DBUser:
    """get an existing user by ID"""

    with ENGINE.begin() as cnx:
        statement = select(
            database.users
        ).where(
            database.users.c.user_id == user_id
        )
        user = DBUser(**cnx.execute(statement).one()._asdict())
        return user


@router.put("/users/{user_id}/", status_code=200)
def update_user(user_id: str, user_request: UpdateUserRequest) -> None:
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
