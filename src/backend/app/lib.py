import numpy as np
import pandas as pd

from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select

from backend.app import database
from backend.app.constants import engine, openai_client, users_collab_collection, movies_collab_collection, movies_content_retriever, QUERY_SCORE_WEIGHT
from shared.models import Movie, Recommendation


def embed_query(query: str) -> List[float]:
    """encode a natural language query into an embedding vector"""

    response = openai_client.embeddings.create(input=query, model="text-embedding-ada-002")
    embedding = response.data[0].embedding
    return embedding


def get_movies(tmdb_ids: List[str]) -> List[Movie]:
    """get a list of Movie objects sorted by ID"""

    with engine.begin() as cnx:
        statement = select(database.movies).where(database.movies.c.tmdb_id.in_(tmdb_ids)).order_by(database.movies.c.tmdb_id)
        movies = [Movie(**row._asdict()) for row in cnx.execute(statement).all()]
        return movies


def get_user_recs(user_id: str, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's collaborative filtering embedding"""

    # find the best matches based on the user's collaborative filtering embedding
    user_embedding = users_collab_collection.get(ids=user_id, include=["embeddings"])["embeddings"][0]
    user_matches = movies_collab_collection.query(query_embeddings=user_embedding, n_results=k, include=["embeddings", "distances"])
    user_matches = sorted(zip(user_matches["ids"][0], user_matches["distances"][0]), key=lambda x: x[0])

    # get sorted lists of [movies, scores] by tmdb_id
    movies = get_movies(tmdb_ids=[match[0] for match in user_matches])
    scores = [1.0 - match[1] for match in user_matches]

    # convert the [movie, score] pairs into recommendation objects and return sorted by descending score
    user_recs = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return sorted(user_recs, key=lambda x: x.score, reverse=True)


def get_search_recs(query: str, user_id: Optional[str] = None, k: int = 10) -> List[Recommendation]:
    """get a list of movie recommendations based on a user's search query embedding"""

    # find the best movie matches based on the user's query sorting the result by [tmdb_id]
    query_matches = sorted(movies_content_retriever.retrieve(query), key=lambda x: x.node_id)

    # create an ordered list of movie IDs and a series of [id, score] pairs from the query matches
    query_match_movies = [match.node_id for match in query_matches]
    query_movie_scores = pd.Series(data=[match.score for match in query_matches], index=query_match_movies)

    # get list of movies and a series of scores based on the query matches sorting the result by [tmdb_id]
    query_movies = get_movies(tmdb_ids=query_match_movies)

    if user_id:

        # get the user's CF embedding and the CF embeddings for the query match movies sorted by tmdb_id
        user_cf_embedding = users_collab_collection.get(ids=user_id, include=["embeddings"])["embeddings"][0]
        movie_cf_embeddings = movies_collab_collection.get(ids=query_match_movies, include=["embeddings"])["embeddings"]

        # calculate user-movie scores for the query match movies based on user-movie CF embedding cosine similarity
        user_movie_scores = cosine_similarity(np.array(movie_cf_embeddings), np.array(user_cf_embedding).reshape(1, -1)).squeeze()
        user_movie_scores = pd.Series(data=user_movie_scores, index=query_match_movies)

    else:

        # calculate user-movie scores for the query match movies based on movie popularity scaled onto [0, 1]
        # FIXME: normalize the popularity scores wrt the entire database of movies not just the topK matches
        user_movie_scores = pd.Series(data=[movie.popularity for movie in query_movies], index=[movie.tmdb_id for movie in query_movies])
        user_movie_scores = (user_movie_scores - user_movie_scores.min()) / (user_movie_scores.max() - user_movie_scores.min())

    # re-rank the movie scores using a weighed average of the [query_movie] and [user_movie] scores sorting the result by [tmdb_id]
    combined_movie_scores = (QUERY_SCORE_WEIGHT * query_movie_scores + (1 - QUERY_SCORE_WEIGHT) * user_movie_scores).sort_index()

    # convert the [movie, score] pairs into recommendation objects and return sorted by descending score
    search_recs = [Recommendation(movie=movie, score=score) for movie, score in zip(query_movies, combined_movie_scores)]
    return sorted(search_recs, key=lambda x: x.score, reverse=True)
