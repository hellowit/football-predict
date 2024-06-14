import streamlit as st

import auth

import numpy as np
import pandas as pd
import datetime as dt

import plotly.graph_objects as go

# Page config
auth.set_page_config()


def ordinal(n: int):
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return str(n) + suffix


def rank_icon(rank):
    if rank == 1:
        icon = "🥇"
    elif rank == 2:
        icon = "🥈"
    elif rank == 3:
        icon = "🥉"
    else:
        icon = ""
    return icon


if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"You are viewing as: **{st.session_state.username}**")

    # Metrics
    col0, col1, col2 = st.columns(3)
    col0.metric("Rank", "2", "1")
    col1.metric("Total Score", "35", "3")
    col2.metric("% Accuracy", "99%", "-8%")

    # Create tabs
    (tab0,) = st.tabs(["Scoreboard"])
    with tab0:
        # Get matches
        matches = auth.get_matches()

        # Get predictions
        predictions = auth.get_predictions()
        # Filter latest predictions
        predictions = predictions.loc[predictions["rank"] == 1, :]

        scores = (
            (
                predictions.loc[
                    :,
                    [
                        "username",
                        "rewarded_points",
                    ],
                ]
                .groupby(["username"])
                .sum()
            )
            .sort_values(["rewarded_points", "username"], ascending=[False, True])
            .reset_index()
        )

        scores.loc[:, "rank"] = scores.loc[:, ["rewarded_points"]].rank(
            method="first", ascending=False
        )

        scores = scores.astype({"rank": "int64"})

        for i in range(scores.shape[0]):
            with st.container(border=True):
                score = scores.loc[scores.index[i], :]
                st.markdown(
                    f"""#### {score.loc["username"]}{rank_icon(score.loc["rank"])}"""
                )
                st.markdown(f"""###### Rank: {ordinal(score.loc["rank"])}""")
                st.markdown(f"""###### Score: {score.loc["rewarded_points"]:.0f}""")
