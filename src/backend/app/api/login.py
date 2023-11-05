from fastapi import APIRouter, HTTPException
from sqlalchemy import insert, select, update, delete
from sqlalchemy.exc import NoResultFound
from passlib.context import CryptContext

from backend.app import database
from backend.app.constants import engine
from shared.models import LoginRequest, User


router = APIRouter()
password_context = CryptContext(schemes=["bcrypt"])


@router.post("/login/")
def login_user(login_request: LoginRequest) -> str:
    """authenticate a user login request returning the corresponding user_id"""

    # select the user record corresponding to the login request
    try:
        with engine.begin() as cnx:
            statement = select(database.users).where(database.users.c.email == login_request.email)
            user = User(**cnx.execute(statement).one()._asdict())
    except NoResultFound:
        raise HTTPException(status_code=400, detail=f"user account with email={login_request.email} not found")

    # verify that the user's stored password matches the login request's password and return the user_id
    verified = password_context.verify(login_request.password, user.hashed_password)
    if verified:
        return user.user_id
    else:
        raise HTTPException(status_code=400, detail=f"incorrect password for email={login_request.email}")
