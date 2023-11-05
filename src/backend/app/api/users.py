
from uuid import uuid4
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import insert, select, update, delete
from sqlalchemy.exc import DatabaseError
from passlib.context import CryptContext

from backend.app import database
from backend.app.constants import engine
from backend.app.lib import get_user_recs
from shared.models import AddUserRequest, UpdateUserRequest, User, DisplayRating, AddRatingRequest, AddRatingsResponse, Recommendation


router = APIRouter()
password_context = CryptContext(schemes=["bcrypt"])


@router.post("/users/")
def create_user(user_request: AddUserRequest) -> str:
    """create a new user"""

    with engine.begin() as cnx:

        # check to make sure there's not already an existing user with the same email
        statement = select(database.users).where(database.users.c.email == user_request.email)
        result = cnx.execute(statement).all()
        if result:
            raise HTTPException(status_code=400, detail=f"a user with email={user_request.email} already exists!")

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


@router.get("/users/{user_id}/")
def get_user(user_id: str) -> User:
    """get an existing user by ID"""

    with engine.begin() as cnx:
        statement = select(
            database.users
        ).where(
            database.users.c.user_id == user_id
        )
        user = User(**cnx.execute(statement).one()._asdict())
        return user


@router.put("/users/{user_id}/")
def update_user(user_id: str, user_request: UpdateUserRequest) -> None:
    """update an existing user by ID"""

    with engine.begin() as cnx:
        statement = update(
            database.users
        ).where(
            database.users.c.user_id == user_id
        ).values(
            updated_at=datetime.now(),
            **user_request.model_dump()
        )
        cnx.execute(statement)


@router.delete("/users/{user_id}/")
def delete_user(user_id: str) -> None:
    """delete an existing user by ID"""

    with engine.begin() as cnx:
        statement = delete(
            database.users
        ).where(
            database.users.c.user_id == user_id
        )
        cnx.execute(statement)


@router.get("/users/{user_id}/ratings/")
def get_user_ratings(user_id: str) -> List[DisplayRating]:
    """get ratings for an existing user by ID"""

    with engine.begin() as cnx:
        statement = select(
            database.movies.c.tmdb_id,
            database.movies.c.tmdb_homepage,
            database.movies.c.title,
            database.movies.c.release_date,
            database.ratings.c.rating
        ).select_from(
            database.ratings.join(database.movies, database.ratings.c.tmdb_id == database.movies.c.tmdb_id)
        ).where(
            database.ratings.c.user_id == user_id
        )

        user_ratings = [DisplayRating(**row._asdict()) for row in cnx.execute(statement).all()]
        return user_ratings


@router.post("/users/{user_id}/ratings/")
def add_user_ratings(user_id: str, requests: List[AddRatingRequest]) -> AddRatingsResponse:
    """add ratings for an existing user by ID"""

    cnt_added, cnt_updated = 0, 0
    updated_at = datetime.now()

    for request in requests:
        try:
            with engine.begin() as cnx:
                statement = insert(database.ratings).values(
                    user_id=user_id,
                    tmdb_id=request.tmdb_id,
                    rating=request.rating,
                    updated_at=updated_at,
                )
                result = cnx.execute(statement)
                cnt_added += result.rowcount
        except DatabaseError:
            with engine.begin() as cnx:
                statement = update(database.ratings).where(
                    database.ratings.c.user_id == user_id,
                    database.ratings.c.tmdb_id == request.tmdb_id
                ).values(
                    rating=request.rating,
                    updated_at=updated_at,
                )
                result = cnx.execute(statement)
                cnt_updated += result.rowcount

    response = AddRatingsResponse(cnt_added=cnt_added, cnt_updated=cnt_updated)
    return response


@router.get("/users/{user_id}/recommendations/")
def get_user_recommendations(user_id: str, k: int = 10) -> List[Recommendation]:
    """get unconditional movie recommendations for an existing user by ID"""

    user_recommendations = get_user_recs(user_id=user_id, k=k)
    return user_recommendations
