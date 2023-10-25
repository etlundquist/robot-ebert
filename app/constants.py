import os
import openai
import pinecone
from dotenv import load_dotenv

from app.database import get_prod_engine


QUERY_SCORE_WEIGHT = 0.8

load_dotenv()
pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])
openai.api_key = os.environ["OPENAI_API_KEY"]

engine = get_prod_engine()
collaborative_index = pinecone.Index("collaborative-embeddings")
content_index = pinecone.Index("content-embeddings")
