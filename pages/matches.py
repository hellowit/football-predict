import streamlit as st

import auth

import numpy as np
import pandas as pd
import datetime as dt

import time


def time_to_match(until_datetime, now=None):
    if now is None:
        now = auth.get_datetime_now()
    ttm = until_datetime - now
    if ttm > dt.timedelta(seconds=0):
        days = ttm.days
        hours = ttm.seconds // 3600
        minutes = (ttm.seconds // 60) % 60
        # seconds = ttm.seconds - hours * 3600 - minutes * 60
        ttm_text = f"""**{ttm.days}** days **{hours}** hours **{minutes}** minutes"""
        return ttm_text


def filter_predictions(username=None, rank=None, match=None):
    # Get predictions
    predictions = auth.get_predictions()
    # Filter username
    if username is not None:
        if type(username) is not list:
            username = [username]
        predictions = predictions.loc[predictions["username"].isin(username), :]
    # Filter rank
    if rank is not None:
        if type(rank) is not list:
            rank = [rank]
        predictions = predictions.loc[predictions["rank"].isin(rank), :]
    # Filter matches
    if match is not None:
        if type(match) is not list:
            match = [match]
        predictions = predictions.loc[predictions["match"].isin(match), :]
    return predictions


# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"You are viewing as: **{st.session_state.username}**")
    
    # Create source link
    st.link_button("Source: Wikipedia", "https://en.wikipedia.org/wiki/UEFA_Euro_2024")
    st.caption(
        "Match numbers are based on the order of appearance in the Wikipedia page."
    )
    # Get recent matches
    matches = auth.get_matches()
    # Sort matches by datetime
    matches = matches.sort_values("datetime")
    # Create recent matches
    recent_matches = pd.concat(
        [
            matches.loc[matches["datetime"] <= auth.get_datetime_now(), :].iloc[-3:, :],
            matches.loc[matches["datetime"] >= auth.get_datetime_now(), :].iloc[:3, :],
        ]
    )
    # Get users
    users = auth.get_users()
    # Get predictions
    predictions = auth.get_predictions()
    # Filter latest
    predictions = predictions.loc[predictions["rank"] == 1, :]
    # Create all possible matches and users
    users_matches = matches.loc[:, ["match", "datetime"]].merge(
        users.loc[:, "username"],
        how="cross",
    )
    # Join with perdictions
    users_matches = users_matches.merge(
        predictions.loc[:, ["username", "match", "timestamp"]],
        how="left",
        on=["match", "username"],
    )
    # Find unsubmitted users
    unsubmitted_users_matches = users_matches.loc[
        users_matches["timestamp"].isnull(), :
    ]

    # Create tabs
    tab0, tab1 = st.tabs(["Recent", "All"])
    tab_list = [tab0, tab1]
    match_list = [recent_matches, matches]
    for t in range(len(tab_list)):
        with tab_list[t]:
            for i in range(match_list[t].shape[0]):
                # Get match info
                match = match_list[t]
                match = match.loc[match.index[i], :]
                # Get prediction timestamp
                prediction_timestamp = (
                    predictions.loc[
                        (predictions["username"] == st.session_state.username)
                        & (predictions["match"] == match.loc["match"]),
                        "timestamp",
                    ]
                    .reset_index(drop=True)
                    .get(0)
                )
                with st.container(border=True):
                    # Write match
                    st.caption(match.loc["match"])
                    # Write teams
                    st.markdown(
                        f"""##### {match.loc["home_team"]} vs {match.loc["away_team"]}{" ✅" if prediction_timestamp is not None else ""}"""
                    )
                    # Write score, if available
                    if not np.isnan(match.loc["goals_difference"]):
                        st.markdown(
                            f"""### {match.loc["home_goals"]:.0f} - {match.loc["away_goals"]:.0f}"""
                        )
                    else:
                        st.markdown("### X - X")
                        # Write match begins
                        st.write(
                            f"""Match begins in {time_to_match(match.loc["datetime"])}"""
                        )
                    # Find unsubmitted users for this match
                    unsubmitted_users = unsubmitted_users_matches.loc[
                        unsubmitted_users_matches["match"] == match.loc["match"],
                        "username",
                    ].to_list()
                    if len(unsubmitted_users) > 0:
                        st.caption(f"""Unsubmitted: {", ".join(unsubmitted_users)}""")

                    # Display histogram
                    with st.expander("Statistics"):
                        st.plotly_chart(
                            auth.get_match_histogram(
                                match.loc["match"],
                                st.session_state.username,
                                show_all=(
                                    True
                                    if time_to_match(match.loc["datetime"]) is None
                                    else False
                                ),
                            )
                        )
