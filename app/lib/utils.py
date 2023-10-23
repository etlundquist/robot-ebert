import os
import sys
import json
import openai

import numpy as np
import pandas as pd

from typing import List
from dotenv import load_dotenv
from pinecone import Index
from sqlalchemy import select
from sklearn.metrics.pairwise import cosine_similarity

from app import database
from app.models import Movie, Recommendation
from app.constants import ENGINE, QUERY_SCORE_WEIGHT


load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]


def embed_query(query: str) -> List[float]:
    """convert a natural language query into an embedding vector"""

    response = openai.Embedding.create(model="text-embedding-ada-002", input=query)
    embedding = response["data"][0]["embedding"]
    return embedding


def get_movies(ids: List[str]) -> List[Movie]:
    """get a list of movies by ID"""

    with ENGINE.begin() as cnx:
        statement = select(
            database.movies
        ).where(
            database.movies.c.tmdb_id.in_(ids)
        )
        movies = [Movie(**row._asdict()) for row in cnx.execute(statement).all()]
        return movies


def get_user_recs(collaborative_index: Index, user_id: str, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's collaborative filtering embedding"""

    user_embedding = collaborative_index.fetch(ids=[user_id], namespace="users")["vectors"][user_id]["values"]
    user_matches = collaborative_index.query(vector=user_embedding, namespace="movies", top_k=k)["matches"]

    movies = get_movies(ids=[match["id"] for match in user_matches])
    scores = [match["score"] for match in user_matches]
    recs = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return recs


def get_query_recs(content_index: Index, query: str, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a query's semantic embedding"""

    query_embedding = embed_query(query)
    query_matches = content_index.query(vector=query_embedding, top_k=k)["matches"]

    movies = get_movies(ids=[match["id"] for match in query_matches])
    scores = [match["score"] for match in query_matches]
    recs = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return recs


def get_user_query_recs(collaborative_index: Index, content_index: Index, user_id: str, query: str, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's collaborative filtering embedding and query semantic embedding"""

    query_embedding = embed_query(query)
    query_matches = content_index.query(vector=query_embedding, top_k=k)["matches"]

    user_cf_embedding = collaborative_index.fetch(ids=[user_id], namespace="users")["vectors"][user_id]["values"]
    movie_cf_vectors = collaborative_index.fetch(ids=[match["id"] for match in query_matches], namespace="movies")["vectors"]
    movie_cf_vectors = sorted([(val["id"], val["values"]) for val in movie_cf_vectors.values()], key=lambda x: x[0])
    movie_cf_ids, movie_cf_embeddings = map(list, zip(*movie_cf_vectors))
    user_movie_scores = cosine_similarity(np.array(movie_cf_embeddings), np.array(user_cf_embedding).reshape(1, -1)).squeeze()

    query_movie_scores = pd.Series(data=[match["score"] for match in query_matches], index=[match["id"] for match in query_matches]).sort_index()
    user_movie_scores = pd.Series(data=user_movie_scores, index=movie_cf_ids).sort_index()
    combined_movie_scores = (QUERY_SCORE_WEIGHT * query_movie_scores + (1 - QUERY_SCORE_WEIGHT) * user_movie_scores).sort_values(ascending=False)

    movies = get_movies(ids=combined_movie_scores.index.values.tolist())
    scores = combined_movie_scores.values.tolist()
    recs = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return recs
