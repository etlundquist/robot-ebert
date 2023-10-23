from datetime import datetime
from fastapi import APIRouter
from typing import List
from sqlalchemy import insert, select, update, delete

from app import database
from app.models import Rating
from app.constants import ENGINE

router = APIRouter()


@router.post("/ratings/", status_code=200)
def add_ratings(ratings: List[Rating]) -> None:
    """add a list of new ratings"""

    updated_at = datetime.now()
    with ENGINE.begin() as cnx:
        for rating in ratings:
            statement = insert(
                database.ratings
            ).values(
                updated_at=updated_at,
                **rating.model_dump()
            )
            cnx.execute(statement)


@router.get("/ratings/{user_id}/", status_code=200)
def get_ratings(user_id: str) -> List[Rating]:
    """get ratings for an existing user"""

    with ENGINE.begin() as cnx:
        statement = select(
            database.ratings
        ).where(
            database.ratings.c.user_id == user_id
        )
        ratings = [Rating(**row._asdict()) for row in cnx.execute(statement).all()]
        return ratings


@router.put("/ratings/", status_code=200)
def update_ratings(ratings: List[Rating]) -> None:
    """update a list of existing ratings"""

    updated_at = datetime.now()
    with ENGINE.begin() as cnx:
        for rating in ratings:
            statement = update(
                database.ratings
            ).where(
                database.ratings.c.user_id == rating.user_id,
                database.ratings.c.tmdb_id == rating.tmdb_id
            ).values(
                rating=rating.rating,
                updated_at=updated_at
            )
            cnx.execute(statement)


@router.delete("/ratings/", status_code=200)
def delete_ratings(ratings: List[Rating]) -> None:
    """delete a list of existing ratings"""

    with ENGINE.begin() as cnx:
        for rating in ratings:
            statement = delete(
                database.ratings
            ).where(
                database.ratings.c.user_id == rating.user_id,
                database.ratings.c.tmdb_id == rating.tmdb_id
            )
            cnx.execute(statement)
