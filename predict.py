import streamlit as st

import auth

import numpy as np
import pandas as pd
import datetime as dt

import plotly.graph_objects as go

import time


# def reset_inputs():
#     st.session_state.input_prediction = 0
#     st.session_state.input_confidence_level = [
#         k for k, v in auth.confidence_levels.items() if v == 0.5
#     ][0]
#     manage_extra_points_inputs([""])
#     st.session_state.reset_inputs = False


def manage_extra_points_inputs(key):
    # Unselect other extra points inputs
    for k in st.session_state:
        if k.find("input_extra_points_") != -1:
            if k != key:
                st.session_state[k] = False


# @st.experimental_dialog("Thank you")
def display_submitted_dialog():
    st.balloons()
    st.toast("Prediction Submitted!", icon="😃")


def display_unsubmitted_matches():
    # Get future matches
    future_matches = auth.get_future_matches(3)
    # Get pridictions
    predictions = auth.get_predictions()
    # Filter latest
    predictions = predictions.loc[predictions["rank"] == 1, :]
    # Filter username
    user_predictions = predictions.loc[
        predictions["username"] == st.session_state.username, :
    ]
    # Find unsubmitted predictions
    unsubmitted_matches = (
        future_matches.loc[:, ["match", "datetime"]]
        .set_index("match")
        .join(
            user_predictions.loc[:, ["match", "timestamp"]].set_index("match"),
            how="left",
        )
    )
    unsubmitted_matches = unsubmitted_matches.loc[
        unsubmitted_matches["timestamp"].isnull(), :
    ]
    for match in unsubmitted_matches.index:
        st.toast(f"Please submit your prediction for **{match}**.", icon="⚽️")


# Page config
auth.set_page_config()

if "initial" not in st.session_state:
    st.session_state.initial = True

# if "reset_inputs" not in st.session_state:
#     st.session_state.reset_inputs = False

# if st.session_state.reset_inputs:
#     reset_inputs()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if auth.get_username() is None:
    auth.display_user_login()
else:
    if st.session_state.initial:
        st.session_state.initial = False
        st.toast(f"""Welcome **{st.session_state.username}**!""", icon="😃")
        display_unsubmitted_matches()
        # reset_inputs()
    # Display submitted dialog
    if st.session_state.submitted:
        st.session_state.submitted = False
        display_submitted_dialog()
    st.markdown(f"You are viewing as: **{st.session_state.username}**")

    # Get future matches
    future_matches = auth.get_future_matches(3)
    # Check if there is any available future matches
    if future_matches.shape[0] == 0:
        st.markdown("There is no more matches to predict!")
    else:
        # Select a match
        match = st.selectbox(
            "Match:",
            options=future_matches.loc[:, "match"],
            index=0,
            key="input_match",
            # on_change=reset_inputs,
        )
        # Get teams
        home_team = future_matches.loc[
            future_matches["match"] == match, "home_team"
        ].iloc[0]
        away_team = future_matches.loc[
            future_matches["match"] == match, "away_team"
        ].iloc[0]
        # Get predictions
        predictions = auth.get_predictions()
        # Filter latest
        predictions = predictions.loc[predictions["rank"] == 1, :]
        # Filter username
        user_predictions = predictions.loc[
            predictions["username"] == st.session_state.username, :
        ]
        # Get the latest submitted prediction
        try:
            displayed_values = (
                user_predictions.loc[user_predictions["match"] == match, :]
                .iloc[0, :]
                .to_dict()
            )
        except:
            # Default values, if latest prediction is not available
            displayed_values = {
                "prediction": 0,
                "extra_points": None,
            }

        # Create tabs
        tab0, tab1 = st.tabs(["New Prediction", "Statistics"])
        with tab0:
            st.markdown(f"You are predicting:")
            st.markdown(
                f"""##### {home_team} vs {away_team}{" ✅" if displayed_values.get("timestamp") is not None else ""}"""
            )

            # Goals difference input
            # prediction = st.slider(
            #     "Prediction (Goals Difference):",
            #     min_value=-7,
            #     max_value=7,
            #     # value=0,
            #     value=displayed_values["prediction"],
            #     key="input_prediction",
            # )
            prediction = st.select_slider(
                "Prediction (Goals Difference):",
                options=[i for i in range(7, -8, -1)],
                # value=0,
                value=displayed_values["prediction"],
                key="input_prediction",
            )
            if prediction > 0:
                st.caption(
                    f"""Definition: {home_team} will win by {prediction} goals."""
                )
            elif prediction < 0:
                st.caption(
                    f"""Definition: {away_team} will win by {prediction*-1} goals."""
                )
            else:
                st.caption(f"""Definition: This match will be a tie.""")

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
            extra_points_availabilities = extra_points_usage_limits.loc[
                :, "available"
            ].to_dict()

            extra_points = {}
            auth.display_checkbox_group("Extra Points:")
            with st.container(border=True):
                # Iterate over extra points items
                for k, _ in auth.extra_points_items.items():
                    extra_points[k] = st.toggle(
                        auth.extra_points_items[k]["name"],
                        # value=False,
                        value=True if displayed_values["extra_points"] == k else False,
                        key=f"input_{k}",
                        on_change=manage_extra_points_inputs,
                        args=(f"input_{k}",),
                        disabled=(
                            True
                            if (extra_points_availabilities[k] == 0)
                            and (displayed_values["extra_points"] != k)
                            else False
                        ),
                    )
                    st.caption(
                        f"""You have {extra_points_availabilities[k]:.0f} left"""
                    )

            # Specify which extra points item is used
            extra_points = [
                k.replace("input_", "") for k, v in extra_points.items() if v
            ]
            extra_points = None if extra_points == [] else extra_points[0]

            # Confidence level input
            # confidence_level = st.select_slider(
            #     "Confidence Level:",
            #     options=[k for k, v in auth.confidence_levels.items()],
            #     # value=[k for k, v in auth.confidence_levels.items() if v == 0.5][0],
            #     value=[
            #         k
            #         for k, v in auth.confidence_levels.items()
            #         if v == displayed_values["confidence_level"]
            #     ][0],
            #     key="input_confidence_level",
            #     help="This does not impact the score calculation, but may be displayed to others just for fun.",
            # )

            with st.expander("What does your prediction mean?", expanded=False):
                # Explain about the prediction number
                st.markdown(f"""Your prediction is **{prediction}**.""")
                if prediction > 0:
                    st.markdown(
                        f"This means you predicted that **{home_team}** will score **{prediction}** goals more than **{away_team}**."
                    )
                elif prediction == 0:
                    st.markdown(
                        f"This means you predicted that **{home_team}** will score the same number of goals as **{away_team}**."
                    )
                else:
                    st.markdown(
                        f"This means you predicted that **{home_team}** will score **{prediction*-1}** goals less than **{away_team}**."
                    )

                # Get rewarded points
                rewarded_points = auth.get_total_points(extra_points)

                # Explain about the extra points items
                if extra_points == "extra_points_mult_3":
                    st.markdown(
                        f"""You also use **{auth.extra_points_items[extra_points]["name"]}**, which will multiply your rewarded points by the factor of 2."""
                    )

                elif extra_points == "extra_points_add_10":
                    st.markdown(
                        f"""You also use **{auth.extra_points_items[extra_points]["name"]}**, which will add 10 additional points to your rewarded points. However, this will subtract 10 points from your rewarded points if your prediction is totally wrong."""
                    )
                # Example rewarded points
                st.markdown(
                    f"""
                    Points will be rewarded as below:
                    
                    |Outcome|Points|
                    |---|---|
                    |Correct goals difference (e.g., 3-2, 1-2)|{rewarded_points["Correct"]}|
                    |Correct goals difference - Tied (e.g., 0-0, 2-2)|{rewarded_points["Correct - Tied"]}|
                    |Correct winning team, but wrong goals difference|{rewarded_points["Partial Correct"]}|
                    |Totally wrong|{rewarded_points["Totally Wrong"]}|
                    """
                )
                auth.display_vertical_spaces(1)

            if st.button(
                "Submit",
                type="primary",
            ):
                with st.spinner():
                    # Create prediction dict
                    temp_prediction = {
                        "timestamp": auth.get_datetime_now(),
                        "username": st.session_state.username,
                        "match": match,
                        "prediction": prediction,
                        "extra_points": extra_points,
                        # "confidence_level": auth.confidence_levels[confidence_level],
                    }
                    # Add prediction to database
                    if auth.add_firestore_documents(
                        collection="predictions",
                        document_data=temp_prediction,
                    ):
                        # Force reset inputs on next rerun
                        # st.session_state.reset_inputs = True
                        # Force display submitted dialog on next rerun
                        st.session_state.submitted = True
                        # Force clear function cache
                        auth.get_predictions.clear()
                        # Add log
                        auth.add_firestore_documents(
                            collection="logs",
                            document_data={
                                "timestamp": auth.get_datetime_now(),
                                "username": st.session_state.username,
                                "action": "submit",
                                "status": "completed",
                            },
                        )
                        st.rerun()
        with tab1:
            st.markdown(f"You are viewing:")
            st.markdown(
                f"""##### {home_team} vs {away_team}{" ✅" if displayed_values.get("timestamp") is not None else ""}"""
            )
            # Filter predictions for current match
            match_predictions = predictions.loc[predictions["match"] == match, :]
            match_predictions = match_predictions.set_index("username")

            # df = (
            #     match_predictions.loc[:, ["prediction"]]
            #     .value_counts()
            #     .rename("count")
            #     .reset_index()
            # )
            # # Create plotly plot
            # fig = go.Figure()
            # # Force display category
            # fig.add_trace(
            #     go.Bar(
            #         x=[i for i in range(-7, 8, 1)],
            #         y=[0 for _ in range(-7, 8, 1)],
            #         showlegend=False,
            #     ),
            # )
            # # Iterate each user's prediction
            # for confidence_level_text in df.loc[
            #     :, "confidence_level_text"
            # ].drop_duplicates():
            #     fig.add_trace(
            #         go.Bar(
            #             x=df.loc[
            #                 df["confidence_level_text"] == confidence_level_text,
            #                 "prediction",
            #             ],
            #             y=df.loc[
            #                 df["confidence_level_text"] == confidence_level_text,
            #                 "count",
            #             ],
            #             name=confidence_level_text,
            #             marker_color=auth.bar_color[confidence_level_text],
            #         ),
            #     )
            # fig.update_layout(
            #     barmode="stack",
            #     hoverlabel=dict(
            #         font_size=14,
            #     ),
            #     showlegend=True,
            #     legend=dict(
            #         orientation="h",
            #         # entrywidth=70,
            #         yanchor="bottom",
            #         y=1.02,
            #         xanchor="right",
            #         x=1,
            #     ),
            # )
            # fig.update_yaxes(
            #     title_text="Number of Predictions",
            #     title_font=dict(size=12, color="rgb(150, 150, 150)"),
            #     dtick=1,
            # )
            # fig.update_xaxes(
            #     # showgrid=True,
            #     ticks="outside",
            #     tickson="boundaries",
            #     ticklen=15,
            #     title_text="Prediction (Goals Difference)",
            #     title_font=dict(size=12, color="rgb(150, 150, 150)"),
            #     tickmode="array",
            #     tickvals=[i for i in range(-7, 8, 1)],
            #     type="category",
            #     griddash="solid",
            # )
            # st.plotly_chart(fig)

            fig = go.Figure()
            # Force display category
            fig.add_trace(
                go.Bar(
                    x=[i for i in range(-7, 8, 1)],
                    y=[0 for _ in range(-7, 8, 1)],
                    showlegend=False,
                ),
            )
            # Iterate each user's prediction
            for i in range(match_predictions.shape[0]):
                row_index = match_predictions.index[i]
                extra_points = match_predictions.loc[row_index, "extra_points"]
                fig.add_trace(
                    go.Bar(
                        x=[match_predictions.loc[row_index, "prediction"]],
                        y=[1],
                        # name=row_index,
                        # legendgroup=extra_points,
                        # legendgrouptitle_text=extra_points,
                        # marker_color=auth.get_bar_color(extra_points)
                        showlegend=False,
                        marker_color="rgb(99, 110, 250)",
                    ),
                )
            fig.update_layout(
                barmode="stack",
            )
            fig.update_yaxes(
                title_text="Number of Predictions",
                title_font=dict(size=12, color="rgb(150, 150, 150)"),
                dtick=1,
                fixedrange=True,
            )
            fig.update_xaxes(
                # showgrid=True,
                ticks="outside",
                tickson="boundaries",
                ticklen=15,
                title_text="Prediction (Goals Difference)",
                title_font=dict(size=12, color="rgb(150, 150, 150)"),
                tickmode="array",
                tickvals=[i for i in range(-7, 8, 1)],
                type="category",
                griddash="solid",
                fixedrange=True,
                autorange="reversed",
                tickangle=0,
            )
            st.plotly_chart(fig)
