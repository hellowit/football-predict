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
        ttm_text = f"""{ttm.days} Days {hours} Hours {minutes} Minutes"""
        return ttm_text


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
    tab0, tab1 = st.tabs(["Recent", "All"])
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
    with tab0:
        for i in range(recent_matches.shape[0]):
            match = recent_matches.loc[recent_matches.index[i], :]
            with st.container(border=True):
                st.caption(match.loc["match"])
                # Write teams
                st.markdown(
                    f"""##### {match.loc["home_team"]} - {match.loc["away_team"]}"""
                )
                # Write score, if available
                if not np.isnan(match.loc["goals_difference"]):
                    st.markdown(
                        f"""### {match.loc["home_goals"]:.0f} - {match.loc["away_goals"]:.0f}"""
                    )
                else:
                    st.markdown("### X - X")
                # Find unsubmitted users for this match
                unsubmitted_users = unsubmitted_users_matches.loc[
                    unsubmitted_users_matches["match"] == match.loc["match"],
                    "username",
                ].to_list()
                st.write(f"""Match Begins in {time_to_match(match.loc["datetime"])}""")
                if len(unsubmitted_users) > 0:
                    st.caption(f"""Unsubmitted users: {", ".join(unsubmitted_users)}""")

    with tab1:
        for i in range(matches.shape[0]):
            match = matches.loc[matches.index[i], :]
            with st.container(border=True):
                st.caption(match.loc["match"])
                # Write teams
                st.markdown(
                    f"""##### {match.loc["home_team"]} - {match.loc["away_team"]}"""
                )
                # Write score, if available
                if not np.isnan(match.loc["goals_difference"]):
                    st.markdown(
                        f"""### {match.loc["home_goals"]:.0f} - {match.loc["away_goals"]:.0f}"""
                    )
                else:
                    st.markdown("### X - X")
                # Find unsubmitted users for this match
                unsubmitted_users = unsubmitted_users_matches.loc[
                    unsubmitted_users_matches["match"] == match.loc["match"],
                    "username",
                ].to_list()
                st.write(f"""Match Begins in {time_to_match(match.loc["datetime"])}""")
                if len(unsubmitted_users) > 0:
                    st.caption(f"""Unsubmitted users: {", ".join(unsubmitted_users)}""")
