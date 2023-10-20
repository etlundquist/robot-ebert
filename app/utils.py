import os
import sys
import json
import openai
import pinecone

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


def embed_query(query: str) -> List[float]:
    """convert a natural language query into an embedding vector"""

    response = openai.Embedding.create(model="text-embedding-ada-002", input=query)
    embedding = response["data"][0]["embedding"]
    return embedding


def get_movies(index: pinecone.Index, ids: List[str]) -> List[Movie]:
    """get a list of movies by ID"""

    vectors = index.fetch(ids=ids)["vectors"]
    movies = [
        Movie(
            id=val["id"],
            title=val["metadata"]["title"],
            release_date=val["metadata"]["release_date"],
            runtime=val["metadata"]["runtime"],
            overview=val["metadata"]["overview"],
            genres=val["metadata"]["genres"],
            keywords=val["metadata"]["keywords"]
        )
        for val in vectors.values()
    ]
    return movies
