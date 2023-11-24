import os
import openai
import chromadb

from dotenv import load_dotenv
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from backend.app.database import get_prod_engine


QUERY_SCORE_WEIGHT = 0.9

load_dotenv()

# create LLM and VectorDB clients
openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
chroma_client = chromadb.PersistentClient(path="./chroma")

# create collection-specific VectorDB clients
embedding_function = OpenAIEmbeddingFunction(api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-ada-002")
movies_content_index = chroma_client.get_collection(name="movies-content", embedding_function=embedding_function)
users_collab_index = chroma_client.get_collection(name="users-collab", embedding_function=embedding_function)
movies_collab_index = chroma_client.get_collection(name="movies-collab", embedding_function=embedding_function)

# create SQLDB engine
engine = get_prod_engine()
