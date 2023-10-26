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


# define helper functions
# -----------------------

def format_recommendations(recommendations: List[Recommendation]) -> DataFrame:
    """convert the returned set of recommendations into a DataFrame for display"""

    recommendations_df = pd.DataFrame([rec.movie.model_dump() for rec in recommendations])
    recommendations_df["score"] = [rec.score for rec in recommendations]
    recommendations_df = recommendations_df.sort_values("score", ascending=False).reset_index().rename(columns={"index": "rank"})
    recommendations_df = recommendations_df[st.session_state["recommendation_columns"]]
    return recommendations_df


@st.cache_data
def get_user_ratings(user_id: str) -> DataFrame:
    """get the user's current set of ratings"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/ratings/"

    ratings_response = session.get(endpoint)
    ratings_response.raise_for_status()

    user_ratings = pd.DataFrame(ratings_response.json())
    return user_ratings


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

def submit_signup():
    """process a signup form submission"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/"
    payload = {
        "fname": st.session_state["signup_fname"],
        "lname": st.session_state["signup_lname"],
        "email": st.session_state["signup_email"],
        "password": st.session_state["signup_password"]
    }

    try:
        signup_response = session.post(endpoint, json=payload)
        signup_response.raise_for_status()
        st.session_state["user_login"] = True
        st.session_state["user_id"] = signup_response.json()
        st.success("Signup Successful!", icon="🎉")
    except HTTPError as err:
        st.error("Signup Failed!", icon="🚨")


def submit_login():
    """process a login form submission"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/login/"
    payload = {
        "email": st.session_state["login_email"],
        "password": st.session_state["login_password"]
    }

    try:
        login_response = session.post(endpoint, json=payload)
        login_response.raise_for_status()
        st.session_state["user_login"] = True
        st.session_state["user_id"] = login_response.json()
        st.success("Login Successful!", icon="🎉")
    except HTTPError as err:
        st.error("Login Failed!", icon="🚨")


def callback_search_query():
    """execute a search query and update the dataframe of search results in the session state"""

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

    user_ratings = get_user_ratings(st.session_state["user_id"])
    st.markdown("### Current User Ratings")
    st.divider()
    st.dataframe(data=user_ratings, use_container_width=True, hide_index=True)


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

# placeholder for search results
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
            fname = st.text_input(label="First Name", key="signup_fname")
            lname = st.text_input(label="Last Name", key="signup_lname")
            email = st.text_input(label="Email Address", key="signup_email")
            password = st.text_input(label="Password", key="signup_password", type="password")
            submit = st.form_submit_button(label="Sign Up", use_container_width=True)
            if submit:
                submit_signup()

    # form: login to an existing account
    with st.expander(label="Log In", expanded=False):
        with st.form(key="login", clear_on_submit=False):
            email = st.text_input(label="Email Address", key="login_email")
            password = st.text_input(label="Password", key="login_password", type="password")
            submit = st.form_submit_button(label="Log In", use_container_width=True)
            if submit:
                submit_login()

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
