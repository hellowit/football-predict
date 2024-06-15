import streamlit as st

# from streamlit_gsheets import GSheetsConnection

import numpy as np
import pandas as pd
import datetime as dt
import time

import plotly.graph_objects as go

from google.cloud import firestore
import json

import requests
from bs4 import BeautifulSoup

# Extra points items config
extra_points_items = {
    "extra_points_mult_3": {
        "name": "Points x3",
        "abbr": "x3",
        "operator": "mult",
        "rewarded_points": {
            "Correct": 3,
            "Correct - Tied": 3,
            "Partial Correct": 3,
            "Totally Wrong": 3,
        },
        "usage_limit": 2,
    },
    "extra_points_add_10": {
        "name": "Points +10 (-10 Penalty)",
        "abbr": "+10",
        "operator": "add",
        "rewarded_points": {
            "Correct": 10,
            "Correct - Tied": 10,
            "Partial Correct": 10,
            "Totally Wrong": -10,
        },
        "usage_limit": 2,
    },
}

# Awarded points config
base_points = {
    "Correct": 3,
    "Correct - Tied": 2,
    "Partial Correct": 1,
    "Totally Wrong": 0,
}

# Confidence levels config
# confidence_levels = {
#     "I'm always wrong": 0,
#     "I have a bad feeling about this": 0.25,
#     "50:50": 0.5,
#     "Trust me, I'm an analyst": 0.75,
#     "I can see the future!": 1,
# }


def get_bar_color(extra_points):
    bar_color = {
        "extra_points_mult_2": "rgb(170, 211, 82)",
        "extra_points_mult_3": "rgb(170, 211, 82)",
        "extra_points_add_10": "rgb(99, 110, 250)",
    }
    if extra_points is None:
        color = "rgb(150, 150, 150)"
    else:
        color = bar_color.get(extra_points)
    return color


def get_total_points(extra_points, base_points=base_points):
    # Return base rewarded points if, no extra points item used
    total_points = base_points
    if extra_points is not None:
        if extra_points_items.get(extra_points) is not None:
            # Combine base rewarded points with extra points factor
            total_points = pd.DataFrame(
                {
                    "base": base_points,
                    "factor": extra_points_items[extra_points]["rewarded_points"],
                }
            )
            # Get operator
            operator = extra_points_items[extra_points]["operator"]
            # Calculate new rewarded points, based on operator
            if operator == "mult":
                total_points.loc[:, "rewarded_points"] = (
                    total_points.loc[:, "base"] * total_points.loc[:, "factor"]
                )
            elif operator == "add":
                total_points.loc[:, "rewarded_points"] = (
                    total_points.loc[:, "base"] + total_points.loc[:, "factor"]
                )
            # Convert rewarded points to dict
            total_points = total_points.loc[:, "rewarded_points"]

    return total_points


def get_outcome(prediction, goals_difference):
    if np.isnan(goals_difference):
        outcome = "Not Concluded"
    elif (prediction == 0) & (goals_difference == 0):
        outcome = "Correct - Tied"
    elif prediction == goals_difference:
        outcome = "Correct"
    elif (prediction > 0) & (goals_difference > 0):
        outcome = "Partial Correct"
    elif (prediction < 0) & (goals_difference < 0):
        outcome = "Partial Correct"
    else:
        outcome = "Totally Wrong"
    return outcome


def get_rewarded_points(outcome, extra_points):
    if outcome is None:
        rewarded_points = np.nan
    elif outcome == "Not Concluded":
        rewarded_points = np.nan
    else:
        rewarded_points = get_total_points(extra_points)[outcome]
    return rewarded_points


def set_page_config():
    # Page config
    st.set_page_config(
        page_title="football-predict",
        page_icon="⚽",
        layout="wide",
        # initial_sidebar_state="expanded",
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
        lambda x: np.nan if x.find("–") == -1 else x[: x.find("–")]
    )
    matches.loc[:, "away_goals"] = matches.loc[:, "score"].apply(
        lambda x: np.nan if x.find("–") == -1 else x[x.find("–") + 1 :]
    )
    # Convert columns types
    matches = matches.astype(
        {
            "datetime": "datetime64[ns, Asia/Bangkok]",
            "home_goals": "float64",
            "away_goals": "float64",
        }
    )
    # Create goals difference
    matches.loc[:, "goals_difference"] = (
        matches.loc[:, "home_goals"] - matches.loc[:, "away_goals"]
    )
    # Convert datetime to Bangkok timezone, and goals to number
    # Create match number
    matches.loc[:, "match_number"] = matches.index + 1
    # Create match name
    matches.loc[:, "match"] = (
        matches.loc[:, "match_number"].apply(lambda x: f"{x:02d}")
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


def get_future_matches(n):
    # Get matches
    matches = get_matches()
    # Filter for top 3 future matches only
    future_matches = (
        matches.loc[matches["is_future_match"] == True, :]
        .sort_values("datetime")
        .iloc[:n, :]
    )

    return future_matches


@st.cache_data(ttl=300)
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

    # Test remove this!
    # matches.loc[:, "home_goals"] = matches.loc[:, "home_goals"].fillna(0)
    # matches.loc[:, "away_goals"] = matches.loc[:, "home_goals"].fillna(0)
    # matches.loc[:, "goals_difference"] = matches.loc[:, "goals_difference"].fillna(0)

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


@st.cache_data(ttl=300)
def get_predictions():
    # Get predictions
    predictions = get_firestore_documents(collection="predictions")
    # Convert datetime to local timezone
    predictions = predictions.astype({"timestamp": "datetime64[ns, Asia/Bangkok]"})
    # Create a confidence level definition column
    # predictions.loc[:, "confidence_level_text"] = predictions.loc[
    #     :, "confidence_level"
    # ].map({v: k for k, v in confidence_levels.items()})

    # Get matches
    matches = get_matches()
    # Drop other columns
    matches = matches.loc[
        :,
        [
            "datetime",
            "match",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "goals_difference",
        ],
    ]

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

    valid_predictions.loc[:, "outcome"] = valid_predictions.apply(
        lambda x: get_outcome(x["prediction"], x["goals_difference"]),
        axis=1,
    )

    valid_predictions.loc[:, "rewarded_points"] = valid_predictions.apply(
        lambda x: get_rewarded_points(x["outcome"], x["extra_points"]),
        axis=1,
    )

    # Sort columns by name
    valid_predictions = valid_predictions.reindex(
        sorted(valid_predictions.columns), axis=1
    )

    # Drop datetime column
    # valid_predictions = valid_predictions.drop(columns="datetime")

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


@st.cache_data(ttl=300)
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
        "Grape 🍇",
        "Kiwi 🥝",
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
                            # Add log
                            add_firestore_documents(
                                collection="logs",
                                document_data={
                                    "timestamp": get_datetime_now(),
                                    "username": input_username,
                                    "action": "login",
                                    "status": "completed",
                                },
                            )
                            st.session_state.username = input_username
                            st.rerun()
                        else:
                            st.error("Invalid SecurityKey!")
                            # Add log
                            add_firestore_documents(
                                collection="logs",
                                document_data={
                                    "timestamp": get_datetime_now(),
                                    "username": input_username,
                                    "action": "login",
                                    "status": "invalid securitykey",
                                },
                            )
                    else:
                        st.error("Invalid Username")
                        # Add log
                        add_firestore_documents(
                            collection="logs",
                            document_data={
                                "timestamp": get_datetime_now(),
                                "username": input_username,
                                "action": "login",
                                "status": "invalid username",
                            },
                        )
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
            st.caption("Choose at least 3 items.")
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
                                st.balloons()
                                st.toast("Registration completed!", icon="😃")
                                st.toast("Redirecting to home...", icon="😬")
                                time.sleep(2)
                                # Auto login with registered username
                                st.session_state.username = reg_username
                                # Force clear function cache
                                get_users.clear()
                                # Add log
                                add_firestore_documents(
                                    collection="logs",
                                    document_data={
                                        "timestamp": get_datetime_now(),
                                        "username": reg_username,
                                        "action": "register",
                                        "status": "completed",
                                    },
                                )
                                st.rerun()

                    else:
                        st.error("Username must be 2 characters or more!")


def get_match_histogram(match, username, show_all=False):
    # Get predictions
    predictions = get_predictions()
    # Filter latest
    predictions = predictions.loc[predictions["rank"] == 1, :]
    # Filter predictions for current match
    match_predictions = predictions.loc[predictions["match"] == match, :]
    # Set index to username
    match_predictions = match_predictions.set_index("username")

    # Plotly plot
    fig = go.Figure()
    # Force display category
    fig.add_trace(
        go.Bar(
            x=[i for i in range(-6, 7, 1)],
            y=[0 for _ in range(-6, 7, 1)],
            showlegend=False,
        ),
    )

    # Iterate each user's prediction
    for i in range(match_predictions.shape[0]):
        username = match_predictions.index[i]
        extra_points = match_predictions.loc[username, "extra_points"]
        # Plot differently, if it's user's prediction
        if username == st.session_state.username:
            my_prediction = True
        else:
            my_prediction = False
        fig.add_trace(
            go.Bar(
                x=[match_predictions.loc[username, "prediction"]],
                y=[1],
                name=username if my_prediction | show_all else "Undisclosed",
                # legendgroup=extra_points,
                # legendgrouptitle_text=extra_points,
                # marker_color=auth.get_bar_color(extra_points)
                # showlegend=True if my_prediction else False,
                showlegend=False,
                text=(
                    extra_points_items[extra_points]["abbr"]
                    if (my_prediction | show_all) and (extra_points is not None)
                    else "."
                ),
                texttemplate="%{text}",
                textfont_size=14,
                hovertemplate="%{x}",
                marker_color=(
                    "rgb(230, 70, 70)" if my_prediction else "rgb(99, 110, 250)"
                ),
            ),
        )

    fig.update_layout(
        barmode="stack",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(
            t=20,
            b=60,
        ),
        height=360,
    )
    fig.update_yaxes(
        # title_text="Number of Predictions",
        # title_font=dict(size=12, color="rgb(150, 150, 150)"),
        dtick=1,
        tickfont_size=14,
        fixedrange=True,
    )
    fig.update_xaxes(
        title_text="Prediction (Goals Difference)",
        title_font=dict(size=12, color="rgb(150, 150, 150)"),
        ticks="outside",
        tickson="boundaries",
        ticklen=15,
        tickmode="array",
        tickvals=[i for i in range(-6, 7, 1)],
        tickfont_size=14,
        type="category",
        griddash="solid",
        fixedrange=True,
        autorange="reversed",
        tickangle=0,
    )

    return fig
