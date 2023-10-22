from argparse import ArgumentParser
from sqlalchemy import MetaData, Table, Column, PrimaryKeyConstraint, create_engine
from sqlalchemy.types import ARRAY, Date, DateTime, Double, Integer, Text


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
    parser.add_argument('--database', type=str, default="database.duckdb")
    args = parser.parse_args()
    engine = create_engine(f"duckdb:///{args.database}")
    metadata.create_all(engine)
