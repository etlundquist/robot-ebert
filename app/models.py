from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel


class UserRequest(BaseModel):
    fname: str
    lname: str
    email: str

class User(BaseModel):
    user_id: str
    fname: str
    lname: str
    email: str

class Movie(BaseModel):
    tmdb_id: str
    title: str
    release_date: datetime
    runtime: float
    genres: List[str]
    keywords: List[str]
    overview: str
    budget: int
    revenue: int
    popularity: float
    vote_average: float
    vote_count: int

class Rating(BaseModel):
    user_id: str
    tmdb_id: str
    rating: float

class Recommendation(BaseModel):
    movie: Movie
    score: float
