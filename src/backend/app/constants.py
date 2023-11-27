import os
import openai
import chromadb

from dotenv import load_dotenv
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pandas import DataFrame

from llama_index import ServiceContext
from llama_index.llms import OpenAI
from llama_index.embeddings import OpenAIEmbedding
from llama_index.vector_stores import ChromaVectorStore
from llama_index.indices.vector_store import VectorStoreIndex

from backend.app.database import get_prod_engine

LIKED_MOVIE_SCORE = 3.5
QUERY_SCORE_WEIGHT = 0.9
SIMILARITY_TOP_K = 10

load_dotenv()

engine = get_prod_engine()

openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
chroma_client = chromadb.PersistentClient(path="./chroma")

embedding_function = OpenAIEmbeddingFunction(api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-ada-002")
movies_content_collection = chroma_client.get_collection(name="movies-content", embedding_function=embedding_function)
users_collab_collection = chroma_client.get_collection(name="users-collab", embedding_function=embedding_function)
movies_collab_collection = chroma_client.get_collection(name="movies-collab", embedding_function=embedding_function)

llm = OpenAI(model="gpt-4-1106-preview", temperature=0.1, max_tokens=1000, api_key=os.environ["OPENAI_API_KEY"])
embed_model = OpenAIEmbedding(model="text-embedding-ada-002", api_key=os.environ["OPENAI_API_KEY"])
service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)

movies_content_vector_store = ChromaVectorStore(chroma_collection=movies_content_collection)
movies_content_vector_index = VectorStoreIndex.from_vector_store(vector_store=movies_content_vector_store, service_context=service_context)
movies_content_retriever = movies_content_vector_index.as_retriever(similarity_top_k=SIMILARITY_TOP_K)

movies_collab_embeddings = movies_collab_collection.get(include=["embeddings"])
movies_collab_embeddings = DataFrame(data=movies_collab_embeddings["embeddings"], index=movies_collab_embeddings["ids"])
