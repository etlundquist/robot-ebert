import numpy as np
import pandas as pd

from typing import List, Dict, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from llama_index.llms import ChatMessage, MessageRole

from backend.app import database
from backend.app.constants import engine, openai_client, users_collab_collection, movies_collab_collection, movies_content_chat_engine, movies_collab_embeddings
from backend.app.constants import LIKED_MOVIE_SCORE, QUERY_SCORE_WEIGHT
from shared.models import Movie, Recommendation, SearchResponse


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

    # get the user's ratings
    with engine.begin() as cnx:
        statement = select(database.ratings).where(database.ratings.c.user_id == user_id)
        user_ratings = cnx.execute(statement).all()
        if not user_ratings:
            return []

    # limit the user's ratings to only movies that appear in the movie embeddings dataframe
    # FIXME: automatically add new movies to the [movies] table when upserting movie ratings
    user_ratings = pd.DataFrame(user_ratings)
    user_ratings = user_ratings[user_ratings["tmdb_id"].isin(movies_collab_embeddings.index)]

    # select the movies the user has liked and those the user has not yet rated
    liked_movies = user_ratings[user_ratings["rating"] >= LIKED_MOVIE_SCORE]["tmdb_id"]
    unrated_movies = movies_collab_embeddings.index.difference(user_ratings["tmdb_id"])

    # calculate the average cosine similarity of each candidate movie wrt to the user's liked movies
    pairwise_similarities = cosine_similarity(movies_collab_embeddings.loc[liked_movies], movies_collab_embeddings)
    movie_scores = pd.Series(pairwise_similarities.mean(axis=0), index=movies_collab_embeddings.index)

    # select the top-k movies in terms of average cosine similarity that the user has not yet rated
    recommended_movies = movie_scores.loc[unrated_movies].sort_values(ascending=False)[:k].sort_index()

    # get sorted lists of [movies, scores] by tmdb_id
    movies = get_movies(tmdb_ids=recommended_movies.index.values.tolist())
    scores = recommended_movies.values.tolist()

    # convert the [movie, score] pairs into recommendation objects and return sorted by descending score
    recommendations = [Recommendation(movie=movie, score=score) for movie, score in zip(movies, scores)]
    return sorted(recommendations, key=lambda x: x.score, reverse=True)


def run_search(chat_messages: List[ChatMessage], user_id: Optional[str] = None, k: int = 10) -> SearchResponse:
    """get a list of movie recommendations based on a user's search query embedding"""

    # separate the user's most recent message from the previous chat history
    message = chat_messages[-1].content
    chat_history = chat_messages[:-1]

    print(f"\nNEW USER MESSAGE: {message}")
    print(f"\nCHAT HISTORY: {chat_history}")

    # send the user query to the chat agent for processing
    chat_response = movies_content_chat_engine.chat(message=message, chat_history=chat_history)
    source_nodes = sorted(chat_response.source_nodes, key=lambda x: x.node_id)

    print(f"\nNEW ASSISTANT MESSAGE: {chat_response.response}")

    # # find the best movie matches based on the user's query sorting the result by [tmdb_id]
    # source_nodes = sorted(movies_content_retriever.retrieve(query), key=lambda x: x.node_id)

    # create an ordered list of movie IDs and a series of [id, score] pairs from the query matches
    query_match_movies = [match.node_id for match in source_nodes]
    query_movie_scores = pd.Series(data=[match.score for match in source_nodes], index=query_match_movies)

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

    # convert the [movie, score] pairs into recommendation objects and sort by score descending
    recommendations = [Recommendation(movie=movie, score=score) for movie, score in zip(query_movies, combined_movie_scores)]
    recommendations = sorted(recommendations, key=lambda x: x.score, reverse=True)

    # return the text response message as well as the formatted list of recommendations
    search_response = SearchResponse(message=chat_response.response, recommendations=recommendations)
    return search_response
