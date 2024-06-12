import streamlit as st
from streamlit_gsheets import GSheetsConnection

import numpy as np
import pandas as pd
import datetime as dt
import time

from google.cloud import firestore
import json

import requests
from bs4 import BeautifulSoup

# Extra points config
extra_points_items = {
    "extra_points_mult_2": {
        "name": "Points x2",
        "usage_limit": 2,
    },
    "extra_points_add_10": {
        "name": "Points +10 (-10 Penalty)",
        "usage_limit": 1,
    },
}

# Awarded points config
rewarded_points = {
    "Correct": 3,
    "Correct - Tied": 2,
    "Partial Correct": 1,
    "Totally Wrong": 0,
}

# Confidence levels config
confidence_levels = {
    "I'm always wrong": 0,
    "I have a bad feeling about this": 0.25,
    "50:50": 0.5,
    "Trust me on this": 0.75,
    "I can see the future!": 1,
}


def set_page_config():
    # Page config
    st.set_page_config(
        page_title="football-predict",
        page_icon="⚽",
        initial_sidebar_state="expanded",
    )
    with st.sidebar:
        if st.button("Force Refresh"):
            st.cache_data.clear()


def get_datetime_now():
    now = dt.datetime.now().astimezone(
        tz=dt.timezone(dt.timedelta(hours=7), name="Asia/Bangkok")
    )
    return now


def get_matches_from_wikipedia():
    # Web scrape from Wikipedia
    response = requests.get(url="https://en.wikipedia.org/wiki/UEFA_Euro_2024")
    soup = BeautifulSoup(response.content, "html.parser")

    # Define dataframe
    matches = {
        "score_string": [],
        "local_date_string": [],
        "local_time_string": [],
        "home_team": [],
        "away_team": [],
    }
    # Find all <div class="footballbox">
    match_items = soup.find_all("div", class_="footballbox")
    for match_item in match_items:
        # Find score string
        matches["score_string"].append(
            match_item.find("th", class_="fscore").get_text(strip=True)
        )
        # Find date string, local timezone
        matches["local_date_string"].append(
            match_item.find("div", class_="fdate").get_text(strip=True)
        )
        # Find time string, local timezone
        matches["local_time_string"].append(
            match_item.find("div", class_="ftime").get_text(strip=True)
        )
        # Find home team
        matches["home_team"].append(
            match_item.find("th", class_="fhome").get_text(strip=True)
        )
        # Find away team
        matches["away_team"].append(
            match_item.find("th", class_="faway").get_text(strip=True)
        )

    # Convert to dataframe
    matches = pd.DataFrame(matches)
    # Extract date from string within parenthesis
    matches.loc[:, "local_date"] = matches.loc[:, "local_date_string"].apply(
        lambda x: dt.datetime.strptime(x[x.find("(") + 1 : x.find(")")], "%Y-%m-%d")
    )
    # Extract time
    matches.loc[:, "local_time"] = matches.loc[:, "local_time_string"].apply(
        lambda x: dt.datetime.strptime(x, "%H:%M").time()
    )
    # Convert to datetime with timezone info
    matches.loc[:, "datetime"] = matches.apply(
        lambda x: (
            dt.datetime.combine(x["local_date"], x["local_time"])
            + dt.timedelta(hours=-2)
        ).astimezone(tz=dt.timezone(dt.timedelta(hours=2), name="Europe/Berlin")),
        axis=1,
    )
    # Extract score remove everything after the first parenthesis
    matches.loc[:, "score"] = matches.loc[:, "score_string"].apply(
        lambda x: x if x.find("(") == -1 else x[: x.find("(")]
    )
    # Convert score string, e.g., 0-2, to number of goals
    matches.loc[:, "home_goals"] = matches.loc[:, "score"].apply(
        lambda x: np.nan if x.find("-") == -1 else x[x.find("-") :]
    )
    matches.loc[:, "away_goals"] = matches.loc[:, "score"].apply(
        lambda x: np.nan if x.find("-") == -1 else x[: x.find("-") - 1]
    )
    # Create goals difference
    matches.loc[:, "goals_difference"] = (
        matches.loc[:, "home_goals"] - matches.loc[:, "away_goals"]
    )
    # Convert datetime to Bangkok timezone, and goals to number
    matches = matches.astype(
        {
            "datetime": "datetime64[ns, Asia/Bangkok]",
            "home_goals": "float64",
            "away_goals": "float64",
        }
    )
    # Create match number
    matches.loc[:, "match_number"] = matches.index + 1
    # Create match name
    matches.loc[:, "match"] = (
        matches.loc[:, "match_number"].apply(lambda x: "{:02d}".format(x))
        + " "
        + matches.loc[:, "home_team"]
        + " - "
        + matches.loc[:, "away_team"]
        + " ("
        + matches.loc[:, "datetime"].apply(lambda x: x.strftime("%a, %d %b %H:%M"))
        + ")"
    )
    # Check if match is already happened
    matches.loc[:, "is_future_match"] = matches.loc[:, "datetime"] >= get_datetime_now()

    return matches


@st.cache_data(ttl=600)
def get_matches():
    # Get matches from Wikipedia
    matches = get_matches_from_wikipedia()
    # Drop other columns
    matches = matches.loc[
        :,
        [
            "match_number",
            "match",
            "datetime",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "goals_difference",
            "is_future_match",
        ],
    ]

    return matches


def get_firestore_database():
    db = firestore.Client.from_service_account_info(json.loads(st.secrets["textkey"]))
    return db


def get_firestore_documents(collection):
    database = get_firestore_database()
    df = pd.DataFrame(
        [document.to_dict() for document in database.collection(collection).stream()]
    )
    return df


def add_firestore_documents(collection, document_data, id=None, merge=True):
    database = get_firestore_database()
    database.collection(collection).document(id).set(
        document_data,
        merge=merge,
    )
    return True


@st.cache_data(ttl=30)
def get_predictions():
    # Get predictions
    predictions = get_firestore_documents(collection="predictions")
    # Convert datetime to local timezone
    predictions = predictions.astype({"timestamp": "datetime64[ns, Asia/Bangkok]"})
    # Create a confidence level definition column
    predictions.loc[:, "confidence_level_text"] = predictions.loc[
        :, "confidence_level"
    ].map({v: k for k, v in confidence_levels.items()})

    # Get matches
    matches = get_matches()
    # Drop other columns
    matches = matches.loc[:, ["datetime", "match", "goals_difference"]]

    # Merge predictions with matches
    valid_predictions = predictions.merge(
        matches,
        how="inner",
        left_on="match",
        right_on="match",
    )
    # Drop predictions, if submitted after the match is started
    valid_predictions = valid_predictions.loc[
        valid_predictions["timestamp"] <= valid_predictions["datetime"], :
    ]

    # Rank by latest timestamp group by username and match
    valid_predictions.loc[:, "rank"] = valid_predictions.groupby(["username", "match"])[
        "timestamp"
    ].rank(ascending=False)

    # Sort columns by name
    valid_predictions = valid_predictions.reindex(
        sorted(valid_predictions.columns), axis=1
    )

    return valid_predictions


# def get_data_gsheets(worksheet, usecols, ttl=60):
#     # Connect to Google sheets
#     conn = st.connection("gsheets", type=GSheetsConnection)
#     # Get worksheet
#     df = conn.read(worksheet=worksheet, usecols=usecols, ttl=ttl).dropna(how="all")
#     return df


# def update_data_gsheets(worksheet, data):
#     # Connect to Google sheets
#     conn = st.connection("gsheets", type=GSheetsConnection)
#     # Update worksheet
#     df = conn.update(worksheet=worksheet, data=data)
#     return True


@st.cache_data(ttl=600)
def get_users():
    users = get_firestore_documents(collection="users")
    return users


def get_username():
    if "username" not in st.session_state:
        st.session_state.username = None
    return st.session_state.username


def display_checkbox_group(text):
    st.markdown(
        f"""
        <label aria-hidden='true' class='st-emotion-cache-1jmvea6 e1nzilvr4'>
            <div data-testid='stMarkdownContainer' class='css-16idsys e16nr0p34'>
                <p>{text}</p>
            </div>
        </label>
        """,
        unsafe_allow_html=True,
    )


def display_vertical_spaces(rows):
    for _ in range(rows):
        st.write("")


def display_user_login():
    # SecurityKey list
    securitykey_list = [
        "Avocado 🥑",
        "Banana 🍌",
        "Coconut 🥥",
        "Melon 🍈",
        "Orange 🍊",
        "Pineapple 🍍",
    ]

    # Create tabs
    tab0, tab1 = st.tabs(["Login", "Register"])
    with tab0:
        with st.form(key="login"):
            # Get users
            users = get_users()
            # Username selection
            input_username = st.selectbox(
                "Username:",
                options=users.loc[:, "username"],
                index=None,
                key="input_username",
            )

            # SecurityKey checkboxes
            input_securitykey = {}
            display_checkbox_group("SecurityKey:")
            for key in securitykey_list:
                input_securitykey[key] = st.checkbox(
                    key,
                    key=f"securitykey_{key}",
                )
            # Login button
            if st.form_submit_button(
                "Login",
                type="primary",
            ):
                with st.spinner("Processing..."):
                    if input_username is not None:
                        # Join SecurityKey
                        temp_securitykey = ", ".join(
                            [
                                k[: k.find(" ")]
                                for k, v in input_securitykey.items()
                                if v
                            ]
                        )
                        # Validate password
                        if (
                            temp_securitykey
                            == users.loc[
                                users["username"] == input_username, "password"
                            ].iloc[0]
                        ):
                            st.session_state.username = input_username
                            st.rerun()
                        else:
                            st.error("Invalid SecurityKey!")
                    else:
                        st.error("Invalid Username")
    with tab1:
        with st.form(key="register"):
            # Username
            reg_username = st.text_input(
                "Username:",
                max_chars=20,
                key="reg_username",
            )
            # SecurityKey checkboxes
            reg_securitykey = {}
            display_checkbox_group("SecurityKey:")
            st.caption("Please do not forget your SecurityKey!")
            for key in securitykey_list:
                reg_securitykey[key] = st.checkbox(
                    key,
                    key=f"reg_securitykey_{key}",
                )

            # Register button
            if st.form_submit_button(
                "Register",
                type="primary",
            ):
                with st.spinner("Processing..."):
                    # Join SecurityKey
                    temp_securitykey = ", ".join(
                        [k[: k.find(" ")] for k, v in reg_securitykey.items() if v]
                    )
                    if len(reg_username) >= 2 and temp_securitykey != "":
                        # Get users
                        users = get_users()
                        # Check if username is already taken
                        if users.loc[:, "username"].str.contains(reg_username).any():
                            st.error("This username is not available!")
                        else:
                            # Create user dict
                            temp_user = {
                                "username": reg_username,
                                "password": temp_securitykey,
                            }
                            # Add user to database
                            if add_firestore_documents(
                                collection="users",
                                document_data=temp_user,
                                id=reg_username,
                            ):
                                # Display completed messages
                                st.success("Registration completed!")
                                st.balloons()
                                st.warning("Redirecting to home...")
                                time.sleep(5)
                                # Auto login with registered username
                                st.session_state.username = reg_username
                                # Force clear function cache
                                get_users.clear()
                                st.rerun()

                    else:
                        st.error("Username must be 2 characters or more!")
