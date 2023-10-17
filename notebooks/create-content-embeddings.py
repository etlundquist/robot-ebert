# Databricks notebook source
# MAGIC %md
# MAGIC ### Notebook Set-Up

# COMMAND ----------

# MAGIC %md
# MAGIC #### Import Required Modules

# COMMAND ----------

# %pip install openai pinecone-client python-dotenv

# COMMAND ----------

import os
import json

from typing import List, Dict
from dotenv import load_dotenv

import openai
import pinecone

from pyspark.sql import SparkSession
from pyspark.sql import functions as f
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC #### Get or Create SparkSession

# COMMAND ----------

spark = SparkSession.builder.getOrCreate()
spark.sparkContext.setLogLevel("error")
spark

# COMMAND ----------

# MAGIC %md
# MAGIC #### Load Secrets as Environment Variables

# COMMAND ----------

env_path = "/dbfs/FileStore/env/.env"
load_dotenv(env_path)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Set Constants

# COMMAND ----------

INDEX_NAME = "ct-embed"
INDEX_DIMENSION = 1536

# COMMAND ----------

# MAGIC %md
# MAGIC ### Create Content Embeddings from the Movies Data

# COMMAND ----------

# MAGIC %md
# MAGIC #### Load the Movies Data

# COMMAND ----------

movies_path = "dbfs:/FileStore/data/clean/movies"
movies = spark.read.parquet(movies_path)
movies.show(10)
movies.count()

# COMMAND ----------

# MAGIC %md
# MAGIC #### Limit the Movies to Only Those Appearing in the Training Model Frame

# COMMAND ----------

model_frame_path = "dbfs:/FileStore/data/clean/model_frame"
model_frame = spark.read.parquet(model_frame_path)

training_movies = model_frame.withColumn('movie_id', f.col('movie_id').cast('string')).select('movie_id').distinct()
training_movies.count()

# COMMAND ----------

# MAGIC %md
# MAGIC #### Add a `Text` Field to the Movie Metadata that Combines `overview`, `genres`, `keywords`

# COMMAND ----------

movie_metadata = movies \
    .join(training_movies, on='movie_id', how='inner') \
    .withColumn('genres',   f.when(f.col('genres').isNull(),   f.array().cast('ARRAY<STRING>')).otherwise(f.col('genres'))) \
    .withColumn('keywords', f.when(f.col('keywords').isNull(), f.array().cast('ARRAY<STRING>')).otherwise(f.col('keywords'))) \
    .sort('movie_id')

movie_metadata.show(10)
movie_metadata.count()

# COMMAND ----------

movie_metadata = [
    {
        "id": movie["movie_id"], 
        "title": movie["title"],
        "text": "{} | {} | {}".format(movie['overview'], ", ".join(movie['genres']), ", ".join(movie['keywords']))
    }
    for movie in movie_metadata.collect()
]
movie_metadata[0]

# COMMAND ----------

# MAGIC %md
# MAGIC #### Embed the Movie Text Using OpenAI Embeddings

# COMMAND ----------

openai.api_key = os.environ["OPENAI_API_KEY"]

# COMMAND ----------

movie_embeddings = [
    openai.Embedding.create(
        model="text-embedding-ada-002",
        input=movie["text"]
    )["data"][0]["embedding"] for movie in movie_metadata
]

# COMMAND ----------

len(movie_metadata), len(movie_embeddings)

# COMMAND ----------

movie_vectors = [
    {
        "id": metadata["id"],
        "values": embedding,
        "metadata": {
            "title": metadata["title"],
            "text": metadata["text"]
        }
    }
    for metadata, embedding in zip(movie_metadata, movie_embeddings)
]
len(movie_vectors)
# movie_vectors[0]

# COMMAND ----------

# MAGIC %md
# MAGIC #### Insert the Embeddings into a Pinecone Index

# COMMAND ----------

import pinecone      
pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])   

# COMMAND ----------

# pinecone.delete_index(INDEX_NAME)
# pinecone.create_index(name=INDEX_NAME, dimension=INDEX_DIMENSION, metric='cosine', pods=1, replicas=1, pod_type="p1")

# COMMAND ----------

index = pinecone.Index(INDEX_NAME)
index.describe_index_stats()

# COMMAND ----------

index.upsert(vectors=movie_vectors, batch_size=100)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Spot Check the Embeddings using Similarity Queries

# COMMAND ----------

query = "a movie about tech in san francisco"
query_embedding = openai.Embedding.create(model="text-embedding-ada-002", input=query)["data"][0]["embedding"]
results = index.query(vector=query_embedding, top_k=10, include_values=False, include_metadata=True)["matches"]
results

# COMMAND ----------


