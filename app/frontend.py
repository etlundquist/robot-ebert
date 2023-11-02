import os
import re
import sys
import requests

import numpy as np
import pandas as pd
import streamlit as st

from typing import List
from dotenv import load_dotenv
from requests import HTTPError
from pandas import DataFrame

# FIXME: configure imports to work from top-level package
from models import Movie, Recommendation

# NOTE: load all secrets from environment variables for local development/testing
# NOTE: all variables in .env must be configured as K8s secrets for cloud run deployment
load_dotenv()

# define helper functions
# -----------------------

def get_movie(tmdb_id: str) -> dict:
    """get movie details by ID from the application database"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/movies/{tmdb_id}/"

    response = session.get(endpoint)
    response.raise_for_status()
    return response.json()


def get_movie_tmdb(tmdb_id: str) -> dict:
    """get movie details by ID from the TMDB API"""

    session = st.session_state["http_session"]
    endpoint = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    headers = {"Authorization": f"Bearer {os.environ['TMDB_ACCESS_TOKEN']}"}

    response = session.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def validate_ratings(ratings: DataFrame) -> None:
    """validate a DataFrame of [tmdb_id, rating] ratings"""

    error_template = "rating with tmdb_id={tmdb_id} rating={rating} is invalid"
    for rating in ratings.itertuples():
        error_message = error_template.format(tmdb_id=rating.tmdb_id, rating=rating.rating)
        try:
            get_movie_tmdb(tmdb_id=rating.tmdb_id)
        except HTTPError:
            st.error(error_message)
            raise ValueError(error_message)
        if (rating.rating is None) or (rating.rating < 1.0) or (rating.rating > 5.0):
            st.error(error_message)
            raise ValueError(error_message)


@st.cache_data
def get_user_ratings(user_id: str) -> DataFrame:
    """get the user's current set of ratings"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/ratings/"

    response = session.get(endpoint)
    response.raise_for_status()

    user_ratings = pd.DataFrame(response.json())
    return user_ratings


def add_user_ratings(user_id: str, ratings: List[dict]) -> None:
    """persist= a set of user ratings to the database"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/ratings/"

    response = session.post(endpoint, json=ratings)
    response.raise_for_status()


def format_recommendations(recommendations: List[Recommendation]) -> DataFrame:
    """convert the returned set of recommendations into a DataFrame for display"""

    recs_df = pd.DataFrame([rec.movie.model_dump() for rec in recommendations])
    recs_df["score"] = [rec.score for rec in recommendations]
    recs_df = recs_df.sort_values("score", ascending=False).reset_index().rename(columns={"index": "rank"})
    return recs_df[st.session_state["recommendation_columns"]]


@st.cache_data
def get_user_recommendations(user_id: str) -> DataFrame:
    """get the user's current set of unconditional recommendations"""

    user_id = "1"
    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/recommendations/"
    # FIXME: remove hard-coded user_id once better data is available

    recommendations_response = session.get(endpoint)
    recommendations_response.raise_for_status()

    recommendations = format_recommendations([Recommendation(**item) for item in recommendations_response.json()])
    return recommendations

# define form submission and callback functions
# ---------------------------------------------

def submit_signup(fname: str, lname: str, email: str, password: str):
    """process a signup form submission"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/"
    payload = {"fname": fname, "lname": lname, "email": email, "password": password}

    try:
        response = session.post(endpoint, json=payload)
        response.raise_for_status()
        st.session_state["user_login"] = True
        st.session_state["user_id"] = response.json()
        st.success("Signup Successful!", icon="🎉")
    except HTTPError as err:
        st.error("Signup Failed!", icon="🚨")
        print(err)


def submit_login(email: str, password: str):
    """process a login form submission"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/login/"
    payload = {"email": email, "password": password}

    try:
        response = session.post(endpoint, json=payload)
        response.raise_for_status()
        st.session_state["user_login"] = True
        st.session_state["user_id"] = response.json()
        st.success("Login Successful!", icon="🎉")
    except HTTPError as err:
        st.error("Login Failed!", icon="🚨")
        print(err)


def submit_manual_ratings(manual_ratings: DataFrame):
    """persist updated manual ratings to the database"""

    try:
        validate_ratings(ratings=manual_ratings)
        add_user_ratings(user_id=st.session_state["user_id"], ratings=manual_ratings.to_dict(orient="records"))
        get_user_ratings.clear()
        st.success("Updated Ratings Saved!", icon="🎉")
    except (ValueError, HTTPError) as err:
        st.error("Updated Ratings Invalid!", icon="🚨")
        print(err)


def callback_search_query():
    """execute a search query and update the session state dataframe of search results"""

    search_query = st.session_state["search_query"].strip()
    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/search/"
    payload = {"query": search_query}

    search_response = session.post(endpoint, json=payload)
    search_response.raise_for_status()

    search_results = format_recommendations([Recommendation(**item) for item in search_response.json()])
    st.session_state["search_results"] = search_results

# define dynamic layout rendering functions
# -----------------------------------------

def render_active_tabs():
    """dynamically render the set of tabs for the main content area based on the session state"""

    if st.session_state["user_login"]:
        tab_names = ["Search", "Ratings", "Recommendations"]
        search, ratings, recommendations = st.tabs(tab_names)
        active_tabs = {"search": search, "ratings": ratings, "recommendations": recommendations}
    else:
        tab_names = ["Search"]
        search = st.tabs(tab_names)[0]
        active_tabs = {"search": search}
    return active_tabs


def render_search():
    """render the contents of the [search] tab"""

    # define a text input box which will execute the search via callback function when the user hits enter
    search_query_label = "What do you want to watch?"
    search_query_help = "Describe the type of movie you'd like to watch: genres, keywords, directors/actors, plot, etc."
    st.text_input(key="search_query", on_change=callback_search_query, label=search_query_label, help=search_query_help)
    st.divider()

    # retrieve the search_results dataframe updated by the callback function and format for display
    search_results = st.session_state["search_results"]
    column_config = {"tmdb_homepage": st.column_config.LinkColumn()}
    st.dataframe(data=search_results, use_container_width=True, hide_index=True, column_config=column_config)


def render_ratings():
    """render the contents of the [ratings] tab"""

    # define a container to hold the user's current set of saved movie ratings
    container_user_ratings = st.container()

    # define a two-column layout to let the user update his/her ratings manually or via TMDB import
    col_manual, col_import = st.columns(2)

    # process the manual update logic via form submission
    with col_manual:
        st.markdown("#### Add or Update Movie Ratings Manually")
        with st.form(key="update_manual_ratings", clear_on_submit=False):
            manual_ratings_config = {"tmdb_id": st.column_config.TextColumn(required=True), "rating": st.column_config.NumberColumn(required=True, min_value=1.0, max_value=5.0, step=0.5)}
            manual_ratings = st.data_editor(pd.DataFrame(columns=["tmdb_id", "rating"]), use_container_width=True, hide_index=True, column_config=manual_ratings_config, num_rows="dynamic")
            submit = st.form_submit_button("Save Updated Ratings", use_container_width=True)
            if submit:
                submit_manual_ratings(manual_ratings)

    # process the import update logic via form submission
    with col_import:
        st.markdown("#### Add or Update Movie Ratings from TMDB")
        import_ratings_save = st.button("Import TMDB Ratings", use_container_width=True)
        if import_ratings_save:
            st.success("Ratings Saved!")

    # populate the current set of the user's saved ratings after applying the updates above
    with container_user_ratings:
        user_ratings = get_user_ratings(user_id=st.session_state["user_id"]).sort_values("tmdb_id")
        st.markdown("### Saved Movie Ratings")
        column_config = {"tmdb_homepage": st.column_config.LinkColumn()}
        st.dataframe(data=user_ratings, use_container_width=True, hide_index=True, column_config=column_config)


def render_recommendations():
    """render the contents of the [recommendations] tab"""

    user_recommendations = get_user_recommendations(st.session_state["user_id"])
    st.markdown("### Current User Recommendations")
    st.divider()
    st.dataframe(data=user_recommendations, use_container_width=True, hide_index=True)

# define global page options
# --------------------------

st.set_page_config(page_title="Robot Ebert", page_icon="🤖", layout="wide")
st.header("Robot Ebert", divider=True)

# initialize persistent session state values
# ------------------------------------------

# URL of the FastAPI application backend
if "backend_url" not in st.session_state:
    st.session_state["backend_url"] = os.environ.get("BACKEND_URL", "http://127.0.0.1:8080")

# requests Session object with common headers
if "http_session" not in st.session_state:
    session = requests.Session()
    common_headers = {"accept": "application/json"}
    session.headers.update(common_headers)
    st.session_state["http_session"] = session

# whether or not a user is currently logged in
if "user_login" not in st.session_state:
    st.session_state["user_login"] = False

# placeholder dataframe for search results
if "search_results" not in st.session_state:
    recommendation_columns = ["rank", "score"] + list(Movie.model_fields.keys())
    st.session_state["recommendation_columns"] = recommendation_columns
    st.session_state["search_results"] = pd.DataFrame(columns=recommendation_columns)

# render a static left sidebar
# ----------------------------

with st.sidebar:

    # image: logo image for the app
    st.image("./images/robot-ebert.png", caption="he's more machine now than man...")

    # form: create a new account
    with st.expander(label="Sign Up", expanded=False):
        with st.form(key="signup", clear_on_submit=False):
            fname = st.text_input(label="First Name")
            lname = st.text_input(label="Last Name")
            email = st.text_input(label="Email Address")
            password = st.text_input(label="Password", type="password")
            submit = st.form_submit_button(label="Sign Up", use_container_width=True)
            if submit:
                submit_signup(fname, lname, email, password)

    # form: login to an existing account
    with st.expander(label="Log In", expanded=False):
        with st.form(key="login", clear_on_submit=False):
            email = st.text_input(label="Email Address")
            password = st.text_input(label="Password", type="password")
            submit = st.form_submit_button(label="Log In", use_container_width=True)
            if submit:
                submit_login(email, password)

# render a dynamic tabset for the main content area
# -------------------------------------------------

active_tabs = render_active_tabs()

if "search" in active_tabs:
    with active_tabs["search"]:
        render_search()

if "ratings" in active_tabs:
    with active_tabs["ratings"]:
        render_ratings()

if "recommendations" in active_tabs:
    with active_tabs["recommendations"]:
        render_recommendations()
