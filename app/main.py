import os
import sys
import json
import openai
import logging
import uvicorn
import pinecone

from pprint import pprint
from fastapi import FastAPI
from dotenv import load_dotenv
from typing import List, Dict


app = FastAPI()
log = logging.getLogger(__name__)

env_path = "../.env"
load_dotenv(env_path)

pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])
openai.api_key = os.environ["OPENAI_API_KEY"]

cf_index = pinecone.Index("cf-embed")
ct_index = pinecone.Index("ct-embed")


@app.get("/", status_code=200)
def root():
    """hello world response for the application root"""

    response = {"message": "it's alive!"}
    return response


@app.get("/user_movies", status_code=200)
def get_user_movies(user_id: str, k: int = 10) -> List[Dict]:
    """get top_k movie recommendations for a user based on collaborative filtering embeddings"""

    query_response = cf_index.query(id=user_id, top_k=k, namespace="movies", include_values=False, include_metadata=True)
    if query_response.get("matches"):
        response = [
            {
                "id": match["id"],
                "score": match["score"]
            }
            for match in query_response["matches"]
        ]
    else:
        response = []
    return response


@app.get("/query_movies", status_code=200)
def get_query_movies(query: str, k: int = 10) -> List[Dict]:
    """get top_k movie recommendations for a query based on semantic search embeddings"""

    embedding_response = openai.Embedding.create(model="text-embedding-ada-002", input=query)
    if embedding_response.get("data"):
        query_embedding = embedding_response["data"][0]["embedding"]
        query_response = ct_index.query(vector=query_embedding, top_k=k, include_values=False, include_metadata=True)
        if query_response.get("matches"):
            response = [
                {
                    "id": match["id"],
                    "title": match["metadata"]["title"],
                    "score": match["score"]
                }
                for match in query_response["matches"]
            ]
        else:
            response = []
    else:
        response = []
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
