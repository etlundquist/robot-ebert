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


sys.path.append(os.path.abspath("."))
from shared.models import Movie, Recommendation
# NOTE: hack to fix relative imports for "streamlit run frontend/app/main.py"


load_dotenv()


# define helper functions
# -----------------------

def create_backend_headers() -> dict:
    """create authorization headers for backend API requests"""

    backend_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8080")
    if backend_url.endswith("run.app"):
        import google.auth.transport.requests
        import google.oauth2.id_token
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, backend_url)
        headers = {"Authorization": f"Bearer {id_token}"}
    else:
        headers = {}
    return headers


def create_tmdb_headers() -> dict:
    """create authorization headers for TMDB API requests"""

    headers = {"Authorization": f"Bearer {os.environ['TMDB_ACCESS_TOKEN']}"}
    return headers


def get_movie(tmdb_id: str) -> dict:
    """get movie details by ID from the application database"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/movies/{tmdb_id}/"
    headers = st.session_state["backend_headers"]

    response = session.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def get_movie_tmdb(tmdb_id: str) -> dict:
    """get movie details by ID from the TMDB API"""

    session = st.session_state["http_session"]
    endpoint = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    headers = st.session_state["tmdb_headers"]

    response = session.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def get_request_token() -> str:
    """generate a new TMDB API request token"""

    session = st.session_state["http_session"]
    endpoint = "https://api.themoviedb.org/3/authentication/token/new"
    headers = st.session_state["tmdb_headers"]

    response = session.get(endpoint, headers=headers)
    response.raise_for_status()

    request_token = response.json()["request_token"]
    return request_token


def get_or_create_tmdb_session() -> str:
    """fetch the current TMDB user session or create a new one"""

    if "tmdb_session_id" in st.session_state:
        return st.session_state["tmdb_session_id"]
    else:
        session = st.session_state["http_session"]
        endpoint = "https://api.themoviedb.org/3/authentication/session/new"
        headers = st.session_state["tmdb_headers"]
        params = {"request_token": st.session_state["request_token"]}
        response = session.get(endpoint, params=params, headers=headers)
        try:
            response.raise_for_status()
            session_id = response.json()["session_id"]
            st.session_state["tmdb_session_id"] = session_id
            return session_id
        except HTTPError as err:
            st.error("You must authenticate your TMDB account before importing movie ratings")
            raise err


def get_tmdb_user_ratings() -> List[dict]:
    """fetch user ratings from TMDB with a new user session"""

    # extract HTTP session and set common headers
    session = st.session_state["http_session"]
    headers = st.session_state["tmdb_headers"]

    # get or create a TMDB session
    session_id = get_or_create_tmdb_session()

    # get the accountID for the authenticated user
    endpoint = "https://api.themoviedb.org/3/account"
    params = {"session_id": session_id}
    response = session.get(endpoint, params=params, headers=headers)
    response.raise_for_status()
    account_id = response.json()["id"]

    # get the rated movies for the account
    endpoint = f"https://api.themoviedb.org/3/account/{account_id}/rated/movies"
    params = {"session_id": session_id}
    response = session.get(endpoint, params=params, headers=headers)
    response.raise_for_status()

    # extract the [tmdb_id, rating] pairs from the user's returned ratings
    ratings = [{"tmdb_id": str(result["id"]), "rating": result["rating"] / 2} for result in response.json()["results"]]
    return ratings


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
    headers = st.session_state["backend_headers"]

    response = session.get(endpoint, headers=headers)
    response.raise_for_status()

    user_ratings = pd.DataFrame(response.json())
    return user_ratings


def add_user_ratings(user_id: str, ratings: List[dict]) -> None:
    """persist= a set of user ratings to the database"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/ratings/"
    headers = st.session_state["backend_headers"]

    response = session.post(endpoint, json=ratings, headers=headers)
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

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/{user_id}/recommendations/"
    headers = st.session_state["backend_headers"]

    recommendations_response = session.get(endpoint, headers=headers)
    recommendations_response.raise_for_status()
    recommendations_payload = recommendations_response.json()

    if recommendations_payload:
        recommendations = format_recommendations([Recommendation(**item) for item in recommendations_payload])
        return recommendations
    else:
        return DataFrame()


# define form submission and callback functions
# ---------------------------------------------

def submit_signup(fname: str, lname: str, email: str, password: str):
    """process a signup form submission"""

    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/users/"
    payload = {"fname": fname, "lname": lname, "email": email, "password": password}
    headers = st.session_state["backend_headers"]

    try:
        response = session.post(endpoint, json=payload, headers=headers)
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
    headers = st.session_state["backend_headers"]

    try:
        response = session.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        st.session_state["user_login"] = True
        st.session_state["user_id"] = response.json()
        st.success("Login Successful!", icon="🎉")
    except HTTPError as err:
        st.error("Login Failed!", icon="🚨")
        print(err)


def submit_manual_ratings(manual_ratings: DataFrame):
    """save updated manual ratings to the database"""

    try:
        validate_ratings(ratings=manual_ratings)
        add_user_ratings(user_id=st.session_state["user_id"], ratings=manual_ratings.to_dict(orient="records"))
        get_user_ratings.clear()
        get_user_recommendations.clear()
        st.success("Updated Ratings Saved!", icon="🎉")
    except (ValueError, HTTPError) as err:
        st.error("Updated Ratings Invalid!", icon="🚨")
        print(err)


def submit_import_ratings():
    """save updated imported ratings to the database"""

    try:
        imported_ratings = get_tmdb_user_ratings()
        add_user_ratings(user_id=st.session_state["user_id"], ratings=imported_ratings)
        get_user_ratings.clear()
        get_user_recommendations.clear()
        st.dataframe(pd.DataFrame(imported_ratings), use_container_width=True, hide_index=True)
        st.success("Imported Ratings Saved!", icon="🎉")
    except (ValueError, HTTPError) as err:
        st.error("Error Importing Ratings!", icon="🚨")
        print(err)


def callback_search_query():
    """execute a search query and update the session state dataframe of search results"""

    search_query = st.session_state["search_query"].strip()
    session = st.session_state["http_session"]
    endpoint = f"{st.session_state['backend_url']}/search/"
    headers = st.session_state["backend_headers"]
    payload = {"query": search_query}

    search_response = session.post(endpoint, json=payload, headers=headers)
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
        st.info("Use the editable table below to add movie ratings manually and then hit the button to save your updated movie ratings")
        with st.form(key="update_manual_ratings", clear_on_submit=False):
            submit = st.form_submit_button("Save Updated Movie Ratings", use_container_width=True)
            manual_ratings_config = {"tmdb_id": st.column_config.TextColumn(required=True), "rating": st.column_config.NumberColumn(required=True, min_value=1.0, max_value=5.0, step=0.5)}
            manual_ratings = st.data_editor(pd.DataFrame(columns=["tmdb_id", "rating"]), use_container_width=True, hide_index=True, column_config=manual_ratings_config, num_rows="dynamic")
            if submit:
                submit_manual_ratings(manual_ratings)

    # process the import update logic via form submission
    with col_import:
        st.markdown("#### Add or Update Movie Ratings from TMDB")
        st.info("Authenticate your TMDB account and then hit the button to import your current TMDB movie ratings")
        with st.form(key="update_import_ratings", clear_on_submit=False):
            submit = st.form_submit_button("Import TMDB Movie Ratings", use_container_width=True)
            if submit:
                submit_import_ratings()
            else:
                imported_ratings_placeholder = pd.DataFrame(columns=["tmdb_id", "rating"])
                st.dataframe(imported_ratings_placeholder, use_container_width=True, hide_index=True)

    # populate the current set of the user's saved ratings after applying the updates above
    with container_user_ratings:
        st.markdown("### Saved Movie Ratings")
        user_ratings = get_user_ratings(user_id=st.session_state["user_id"])
        if len(user_ratings) > 0:
            column_config = {"tmdb_homepage": st.column_config.LinkColumn()}
            st.dataframe(data=user_ratings.sort_values("tmdb_id"), use_container_width=True, hide_index=True, column_config=column_config)
        else:
            empty_frame = pd.DataFrame(columns=["tmdb_id", "tmdb_homepage", "title", "release_date", "rating"])
            st.dataframe(data=empty_frame, use_container_width=True, hide_index=True)


def render_recommendations():
    """render the contents of the [recommendations] tab"""

    user_recommendations = get_user_recommendations(st.session_state["user_id"])
    st.markdown("### Top Overall Recommended Movies")
    st.divider()
    st.dataframe(data=user_recommendations, use_container_width=True, hide_index=True)

# define global page options
# --------------------------

st.set_page_config(page_title="RobotEbert", page_icon="🤖", layout="wide")
st.header("RobotEbert", divider=True)

# define custom CSS
# -----------------

custom_css = """
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.5rem;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# initialize persistent session state values
# ------------------------------------------

# URL of the FastAPI application backend
if "backend_url" not in st.session_state:
    st.session_state["backend_url"] = os.environ.get("BACKEND_URL", "http://127.0.0.1:8080")

# requests Session object with common headers
if "http_session" not in st.session_state:

    http_session = requests.Session()
    common_headers = {"accept": "application/json"}
    http_session.headers.update(common_headers)
    st.session_state["http_session"] = http_session
    st.session_state["backend_headers"] = create_backend_headers()
    st.session_state["tmdb_headers"] = create_tmdb_headers()

# indicator for whether or not a user is currently logged in
if "user_login" not in st.session_state:
    st.session_state["user_login"] = False

# placeholder dataframe for search results
if "search_results" not in st.session_state:
    recommendation_columns = ["rank", "score"] + list(Movie.model_fields.keys())
    st.session_state["recommendation_columns"] = recommendation_columns
    st.session_state["search_results"] = pd.DataFrame(columns=recommendation_columns)

# request token to generate TMDB user sessions
if "request_token" not in st.session_state:
    st.session_state["request_token"] = get_request_token()

# render a static left sidebar
# ----------------------------

with st.sidebar:

    # image: logo image for the app
    st.image("frontend/static/robot-ebert.png", caption="he's more machine now than man...")

    # form: create a new account
    with st.expander(label="Sign Up", expanded=False):
        with st.form(key="signup", clear_on_submit=False):
            fname = st.text_input(label="First Name")
            lname = st.text_input(label="Last Name")
            email = st.text_input(label="Email Address")
            password = st.text_input(label="Password", type="password")
            submit_help = "create an account to personalize content"
            submit = st.form_submit_button(label="Sign Up", help=submit_help, use_container_width=True)
            if submit:
                submit_signup(fname, lname, email, password)

    # form: login to an existing account
    with st.expander(label="Log In", expanded=False):
        with st.form(key="login", clear_on_submit=False):
            email = st.text_input(label="Email Address")
            password = st.text_input(label="Password", type="password")
            submit_help = "log in to edit ratings and view recommendations"
            submit = st.form_submit_button(label="Log In", help=submit_help, use_container_width=True)
            if submit:
                submit_login(email, password)

    # link button: authenticate your TMDB account
    tmdb_auth_url = f"https://www.themoviedb.org/authenticate/{st.session_state['request_token']}"
    tmdb_auth_help = "authenticate with TMDB to import movie ratings"
    st.link_button("Authenticate Your TMDB Account", url=tmdb_auth_url, help=tmdb_auth_help, use_container_width=True)

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
