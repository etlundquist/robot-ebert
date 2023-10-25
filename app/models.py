from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AddUserRequest(BaseModel):
    email: str
    password: str
    fname: str
    lname: str

class UpdateUserRequest(BaseModel):
    email: str
    fname: str
    lname: str

class User(BaseModel):
    user_id: str
    email: str
    hashed_password: str
    fname: str
    lname: str
    updated_at: datetime


class Movie(BaseModel):
    tmdb_id: str
    tmdb_homepage: str
    title: str
    language: str
    release_date: datetime
    runtime: int
    director: str
    actors: Optional[List[str]]
    genres: Optional[List[str]]
    keywords: Optional[List[str]]
    overview: str
    budget: int
    revenue: int
    popularity: float
    vote_average: float
    vote_count: int


class UserRating(BaseModel):
    tmdb_id: str
    rating: float

class Rating(BaseModel):
    user_id: str
    tmdb_id: str
    rating: float

class AddRatingsResponse(BaseModel):
    cnt_added: int
    cnt_updated: int


class Recommendation(BaseModel):
    movie: Movie
    score: float
