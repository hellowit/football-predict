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
    # st.write(f"You are viewing as: **{st.session_state.username}**")
    if st.button(f"You are viewing as: **{st.session_state.username}**"):
        st.cache_data.clear()

    # Metrics
    # col0, col1, col2 = st.columns(3)
    # col0.metric("Rank", "2", "1")
    # col1.metric("Total Score", "35", "3")
    # col2.metric("% Accuracy", "99%", "-8%")

    # Create tabs
    (tab0,) = st.tabs(["Scoreboard"])
    with tab0:
        # Get matches
        matches = auth.get_matches()

        # Get predictions
        predictions = auth.get_predictions()
        # Filter latest predictions
        predictions = predictions.loc[predictions["rank"] == 1, :]
        # Filter not future matches only
        predictions = predictions.loc[predictions["is_future_match"] == False, :]
        # accuracy = (
        #     predictions.loc[:, ["username", "outcome"]]
        #     .groupby(["username"])
        #     .value_counts(normalize=True)
        #     .rename("percentage")
        # ).reset_index()
        # accuracy

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
            method="dense", ascending=False
        )

        scores = scores.astype({"rank": "int64"})

        for i in range(scores.shape[0]):
            with st.container(border=True):
                # Filter user's score
                score = scores.loc[scores.index[i], :]
                # Filter user's predictions
                user_predictions = predictions.loc[
                    predictions["username"] == score.loc["username"], :
                ]
                user_predictions = user_predictions.sort_values("datetime")

                # Join usage limits with usage counts
                extra_points_usage_limits = (
                    pd.DataFrame(auth.extra_points_items)
                    .T.join(user_predictions.loc[:, "extra_points"].value_counts())
                    .fillna(0)
                )
                # Calculate extra points items available to use
                extra_points_usage_limits.loc[:, "available"] = (
                    extra_points_usage_limits.loc[:, "usage_limit"]
                    - extra_points_usage_limits.loc[:, "extra_points"]
                )
                extra_points_availabilities = (
                    extra_points_usage_limits.loc[:, "available"]
                    .reset_index()
                    .rename(columns={"index": "extra_points"})
                )
                extra_points_availabilities.loc[:, "extra_points_item"] = (
                    extra_points_availabilities.loc[:, "extra_points"].apply(
                        lambda x: auth.extra_points_items[x]["name"]
                    )
                )

                # Display username
                st.markdown(
                    f"""#### {score.loc["username"]}{rank_icon(score.loc["rank"])}"""
                )

                st.markdown(f"""###### Rank: {ordinal(score.loc["rank"])}""")
                st.markdown(f"""###### Score: {score.loc["rewarded_points"]:.0f}""")

                fig = go.Figure()
                for match in user_predictions.loc[:, "match"]:
                    fig.add_trace(
                        go.Bar(
                            x=user_predictions.loc[
                                user_predictions["match"] == match, "rewarded_points"
                            ],
                            texttemplate="%{x}",
                            textangle=0,
                            hovertemplate="%{x}",
                            name=match,
                            showlegend=False,
                            orientation="h",
                        )
                    )
                fig.update_layout(
                    barmode="stack",
                    showlegend=False,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                    ),
                    margin=dict(
                        t=0,
                        b=0,
                    ),
                    height=30,
                    autosize=True,
                )
                fig.update_yaxes(
                    # dtick=1,
                    # tickfont_size=14,
                    fixedrange=True,
                    visible=False,
                    zeroline=False,
                )
                fig.update_xaxes(
                    # title_text="Prediction (Goals Difference)",
                    # title_font=dict(size=12, color="rgb(150, 150, 150)"),
                    # ticks="outside",
                    # tickson="boundaries",
                    # ticklen=15,
                    # tickmode="array",
                    # tickvals=[i for i in range(-6, 7, 1)],
                    # tickfont_size=14,
                    # type="category",
                    # griddash="solid",
                    fixedrange=True,
                    # autorange="reversed",
                    # tickangle=0,
                    range=(0, scores.loc[:, "rewarded_points"].max()),
                    visible=False,
                    zeroline=False,
                )
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Details", expanded=False):
                    # st.write(predictions.loc[predictions["username"] == score.loc["username"], "extra_points"].value_counts())
                    st.write(
                        predictions.loc[
                            predictions["username"] == score.loc["username"], :
                        ]
                    )
                    st.write(
                        extra_points_availabilities.loc[
                            :, ["extra_points_item", "available"]
                        ].set_index("extra_points_item")
                    )
