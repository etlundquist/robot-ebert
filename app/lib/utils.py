import openai
import numpy as np
import pandas as pd

from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select

from app import database
from app.models import Movie, Recommendation
from app.constants import engine, collaborative_index, content_index, QUERY_SCORE_WEIGHT


def embed_query(query: str) -> List[float]:
    """convert a natural language query into an embedding vector"""

    response = openai.Embedding.create(model="text-embedding-ada-002", input=query)
    embedding = response["data"][0]["embedding"]
    return embedding


def get_movies(tmdb_ids: List[str]) -> List[Movie]:
    """get a list of movies by ID sorted by ID"""

    with engine.begin() as cnx:
        statement = select(database.movies).where(database.movies.c.tmdb_id.in_(tmdb_ids)).order_by(database.movies.c.tmdb_id)
        movies = [Movie(**row._asdict()) for row in cnx.execute(statement).all()]
        return movies


def get_user_recs(user_id: str, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's collaborative filtering embedding"""

    # find the best matches based on the user's collaborative filtering embedding
    user_embedding = collaborative_index.fetch(ids=[user_id], namespace="users")["vectors"][user_id]["values"]
    user_matches = collaborative_index.query(vector=user_embedding, namespace="movies", top_k=k)["matches"]

    # get sorted lists of [movies, scores] by tmdb_id
    movies = get_movies(tmdb_ids=[match["id"] for match in user_matches])
    scores = [match["score"] for match in sorted(user_matches, key=lambda x: x["id"])]

    # convert the [movie, score] pairs into recommendation objects and return sorted by descending score
    user_recs = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return sorted(user_recs, key=lambda x: x.score, reverse=True)


def get_search_recs(query: str, user_id: Optional[str] = None, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's search query embedding"""

    # find the best matches based on the user's search query embedding
    query_embedding = embed_query(query)
    query_matches = content_index.query(vector=query_embedding, top_k=k)["matches"]

    # get list of movies and a series of scores based on the query matches
    query_movies = get_movies(tmdb_ids=[match["id"] for match in query_matches])
    query_movie_scores = pd.Series(data=[match["score"] for match in query_matches], index=[match["id"] for match in query_matches])

    if user_id:

        # get the user's CF embedding and the CF embeddings for the query match movies sorted by tmdb_id
        user_cf_embedding = collaborative_index.fetch(ids=[user_id], namespace="users")["vectors"][user_id]["values"]
        movie_cf_vectors = collaborative_index.fetch(ids=[match["id"] for match in query_matches], namespace="movies")["vectors"]
        movie_cf_vectors = sorted([(val["id"], val["values"]) for val in movie_cf_vectors.values()], key=lambda x: x[0])
        movie_cf_ids, movie_cf_embeddings = map(list, zip(*movie_cf_vectors))

        # calculate user-movie scores for the query match movies based on user-movie CF embedding similarities
        user_movie_scores = cosine_similarity(np.array(movie_cf_embeddings), np.array(user_cf_embedding).reshape(1, -1)).squeeze()
        user_movie_scores = (user_movie_scores - user_movie_scores.min()) / (user_movie_scores.max() - user_movie_scores.min())
        user_movie_scores = pd.Series(data=user_movie_scores, index=movie_cf_ids)

    else:

        # calculate user-movie scores for the query match movies based on movie popularity
        user_movie_scores = pd.Series(data=[movie.popularity for movie in query_movies], index=[movie.tmdb_id for movie in query_movies])
        user_movie_scores = (user_movie_scores - user_movie_scores.min()) / (user_movie_scores.max() - user_movie_scores.min())

    # create combined movie scores as a weighed average of the query-movie and user-movie scores and sort by tmdb_id
    combined_movie_scores = (QUERY_SCORE_WEIGHT * query_movie_scores + (1 - QUERY_SCORE_WEIGHT) * user_movie_scores).sort_index()

    # convert the [movie, score] pairs into recommendation objects and return sorted by descending score
    search_recs = [Recommendation(movie=movie, score=score) for movie, score in zip(query_movies, combined_movie_scores)]
    return sorted(search_recs, key=lambda x: x.score, reverse=True)
