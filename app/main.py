import os
import sys
import json
import openai
import logging
import uvicorn
import pinecone

import numpy as np
import pandas as pd

from pprint import pprint
from fastapi import FastAPI
from dotenv import load_dotenv
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity

from utils import Movie, embed_query, get_movies


app = FastAPI()
log = logging.getLogger(__name__)

env_path = "../.env"
load_dotenv(env_path)

pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])
openai.api_key = os.environ["OPENAI_API_KEY"]

cf_index = pinecone.Index("cf-embed")
ct_index = pinecone.Index("ct-embed")

QUERY_SCORE_WEIGHT = 0.5


@app.get("/", status_code=200)
def root():
    """hello world response for the application root"""

    response = "hello world!"
    return response


@app.get("/user_movies", status_code=200)
def get_user_movies(user_id: str, k: int = 10) -> List[Movie]:
    """get recommended movies using collaborative filtering embedding similarity"""

    user_matches = cf_index.query(id=user_id, top_k=k, namespace="movies", include_values=False, include_metadata=True)["matches"]
    user_movies = get_movies(ct_index, ids=[match["id"] for match in user_matches])
    return user_movies


@app.get("/query_movies", status_code=200)
def get_query_movies(query: str, k: int = 10) -> List[Movie]:
    """get recommended movies using semantic search embedding similarity"""

    query_embedding = embed_query(query)
    query_matches = ct_index.query(vector=query_embedding, top_k=k, include_values=False, include_metadata=True)["matches"]
    query_movies = get_movies(ct_index, ids=[match["id"] for match in query_matches])
    return query_movies


@app.get("/user_query_movies", status_code=200)
def get_user_query_movies(user_id: str, query: str, k: int = 10) -> List[Movie]:
    """get recommended movies using semantic search and collaborative filtering embedding similarity"""

    # fetch query-movie similarity scores for the top query matches
    query_embedding = embed_query(query)
    query_matches = ct_index.query(vector=query_embedding, top_k=k)["matches"]

    # fetch the user's collaborative filtering embedding vector
    user_cf_response = cf_index.fetch(ids=[user_id], namespace="users")
    user_cf_embedding = user_cf_response["vectors"][user_id]["values"]

    # fetch the query match movies' collaborative filtering embedding vectors
    query_movie_ids = [match["id"] for match in query_matches]
    movie_cf_vectors = cf_index.fetch(ids=query_movie_ids, namespace="movies")["vectors"]
    movie_cf_vectors = sorted([(val["id"], val["values"]) for val in movie_cf_vectors.values()], key=lambda x: x[0])
    movie_cf_ids, movie_cf_embeddings = map(list, zip(*movie_cf_vectors))

    # calculate user-movie similarity scores for each query match movie
    user_movie_scores = cosine_similarity(np.array(movie_cf_embeddings), np.array(user_cf_embedding).reshape(1, -1)).squeeze()

    # combine the query-movie and user-movie similarity scores into a final combined score
    query_movie_scores = pd.Series(data=[match["score"] for match in query_matches], index=[match["id"] for match in query_matches]).sort_index()
    user_movie_scores = pd.Series(data=user_movie_scores, index=movie_cf_ids).sort_index()
    combined_movie_scores = (QUERY_SCORE_WEIGHT * query_movie_scores + (1 - QUERY_SCORE_WEIGHT) * user_movie_scores).sort_values(ascending=False)

    # fetch metadata for the combined score movies
    combined_movies = get_movies(ct_index, ids=combined_movie_scores.index.values.tolist())
    return combined_movies


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
