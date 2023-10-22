from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel


class Movie(BaseModel):
    id: str
    title: str
    release_date: datetime
    runtime: float
    overview: str
    genres: List[str]
    keywords: List[str]

class MovieScore(BaseModel):
    movie: Movie
    score: float
