import os
import re
import sys
import requests

import numpy as np
import pandas as pd
import streamlit as st

from typing import TypedDict
from dotenv import load_dotenv

# FIXME: configure imports to work from top-level package
from models import Movie


# define form submission and callback functions
# ---------------------------------------------

def submit_signup():
    """process a signup form submission"""

    if st.session_state["signup_fname"] == "Eric":
        st.success("Account Creation Successful!", icon="🎉")
    else:
        st.error("Account Creation Failed!", icon="🚨")


def submit_login():
    """process a login form submission"""

    if st.session_state["login_email"] == "e.t.lundquist@gmail.com":
        st.success("Login Successful!", icon="🎉")
        st.session_state["user_login"] = True
        st.session_state["user_id"] = "1"
        st.session_state["user_token"] = "1111-2222-3333-4444"
    else:
        st.error("Login Failed!", icon="🚨")


def callback_search_query():
    """process a search query"""

    search_query = st.session_state["search_query"].strip()
    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/search/"
    payload = {"query": search_query}

    search_response = session.post(endpoint, json=payload)
    search_response.raise_for_status()

    search_results_json = search_response.json()
    search_results_df = pd.DataFrame([item["movie"] for item in search_results_json])
    search_results_df["score"] = [item["score"] for item in search_results_json]
    search_results_df = search_results_df.sort_values("score", ascending=False).reset_index().rename(columns={"index": "rank"})
    st.session_state["search_results"] = search_results_df[st.session_state["search_results_columns"]]


# define dynamic layout rendering functions
# -----------------------------------------

def render_tabs():
    """dynamically render the set of tabs for the main content area based on the session state"""

    if st.session_state["user_login"]:
        tab_names = ["Search", "Ratings", "Recommendations"]
        search, ratings, recommendations = st.tabs(tab_names)
        current_tabs = {"search": search, "ratings": ratings, "recommendations": recommendations}
    else:
        tab_names = ["Search"]
        search = st.tabs(tab_names)
        current_tabs = {"search": search}
    return current_tabs


def render_search():
    """render the contents of the [search] tab"""

    # define a text input box which will execute the search via callback function when the user hits enter
    search_query_label = "What do you want to watch?"
    search_query_help = "Describe the type of movie you'd like to watch: genres, keywords, directors/actors, plot, etc."
    st.text_input(label=search_query_label, key="search_query", help=search_query_help, on_change=callback_search_query)
    st.divider()

    # retrieve the search_results dataframe updated by the callback function and format for display
    search_results = st.session_state["search_results"]
    column_config = {
        "tmdb_homepage": st.column_config.LinkColumn(),
        "title": st.column_config.TextColumn(),
        "overview": st.column_config.TextColumn()
    }
    st.dataframe(data=search_results, use_container_width=True, hide_index=True, column_config=column_config)





# define global page options
# --------------------------

st.set_page_config(page_title="Robot Ebert", page_icon="🤖", layout="wide")
st.header("Robot Ebert", divider=True)
st.subheader("Chat with an AI Agent to get personalized movie recommendations")

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
    search_results_columns = ["rank", "score"] + list(Movie.model_fields.keys())
    st.session_state["search_results_columns"] = search_results_columns
    st.session_state["search_results"] = pd.DataFrame(columns=search_results_columns)

# define the main navigation sidebar
# ----------------------------------

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

# define the tabset for the main content area
# -------------------------------------------

current_tabs = render_tabs()

if "search" in current_tabs:
    with current_tabs["search"][0]:
        render_search()

