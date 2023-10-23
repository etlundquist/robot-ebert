import os

from argparse import ArgumentParser
from sqlalchemy import MetaData, Table, Column, PrimaryKeyConstraint, Engine, create_engine
from sqlalchemy.types import ARRAY, Date, DateTime, Double, Integer, Text
from google.cloud.sql.connector import Connector
from dotenv import load_dotenv
from pg8000 import Connection


load_dotenv()


def make_connection() -> Connection:
    """generate a new pg8000 connection for a CloudSQL instance"""

    project = "robot-ebert"
    region = "us-west1"
    instance = "robot-ebert"
    instance_connection_string = f"{project}:{region}:{instance}"

    connector = Connector()
    cnx = connector.connect(
        instance_connection_string=instance_connection_string,
        driver="pg8000",
        user="postgres",
        password=os.environ["POSTGRES_PASSWORD"],
        db="app"
    )
    return cnx


def get_engine(test: bool = False, echo: bool = False) -> Engine:
    """get a new SQLAlchemy Engine to manage DB connections"""

    if test:
        engine = create_engine(f"duckdb:///database.duckdb", echo=echo)
    else:
        engine = create_engine("postgresql+pg8000://", creator=make_connection, echo=echo)
    return engine


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("fname", Text),
    Column("lname", Text),
    Column("email", Text),
    Column("updated_at", DateTime)
)

movies = Table(
    "movies",
    metadata,
    Column("tmdb_id", Text, primary_key=True),
    Column("title", Text),
    Column("release_date", Date),
    Column("runtime", Double),
    Column("genres", ARRAY(Text)),
    Column("keywords", ARRAY(Text)),
    Column("overview", Text),
    Column("budget", Integer),
    Column("revenue", Integer),
    Column("popularity", Double),
    Column("vote_average", Double),
    Column("vote_count", Integer),
    Column("updated_at", DateTime)
)

ratings = Table(
    "ratings",
    metadata,
    Column("user_id", Text),
    Column("tmdb_id", Text),
    Column("rating", Double),
    Column("updated_at", DateTime),
    PrimaryKeyConstraint("user_id", "tmdb_id")
)


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("--test", type=bool, default=False)
    parser.add_argument("--echo", type=bool, default=True)

    args = parser.parse_args()
    engine = get_engine(test=args.test, echo=args.echo)
    metadata.create_all(engine)
