import streamlit as st

import auth

import numpy as np
import pandas as pd
import datetime as dt

import time


def reset_inputs():
    st.session_state.input_prediction = 0
    st.session_state.input_confidence_level = [
        k for k, v in auth.confidence_levels.items() if v == 0.5
    ][0]
    manage_extra_points_inputs([""])
    st.session_state.reset_inputs = False


def manage_extra_points_inputs(key):
    # Unselect other extra points inputs
    for k in st.session_state:
        if k.find("input_extra_points_") != -1:
            if k != key:
                st.session_state[k] = False


# @st.experimental_dialog("Thank you")
def display_submitted_dialog():
    st.balloons()
    st.toast("Prediction Submitted!")


def display_unsubmitted_matches():
    # Get matches
    matches = auth.get_matches()
    # Get pridictions
    predictions = auth.get_predictions()
    predictions = predictions.loc[predictions["rank"] == 1, :]
    for i in range(predictions.shape[0]):
        st.toast(predictions.iloc[i, :])


# Page config
auth.set_page_config()

if "initial" not in st.session_state:
    st.session_state.initial = True

if "reset_inputs" not in st.session_state:
    st.session_state.reset_inputs = False

if st.session_state.reset_inputs:
    reset_inputs()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if auth.get_username() is None:
    auth.display_user_login()
else:
    if st.session_state.initial:
        st.session_state.initial = False
        display_unsubmitted_matches()
    # Display submitted dialog
    if st.session_state.submitted:
        st.session_state.submitted = False
        display_submitted_dialog()
    st.write(f"You are viewing as: **{st.session_state.username}**")
    # Create tabs
    (tab0,) = st.tabs(["New Prediction"])
    with tab0:
        # Get matches
        future_matches = auth.get_matches()
        # Filter for top 3 future matches only
        future_matches = future_matches.loc[
            future_matches["is_future_match"] == True, :
        ].sort_values("datetime").iloc[:3, :]

        # Check if there is any available future matches
        if future_matches.shape[0] == 0:
            st.write("There is no more matches to predict!")
        else:
            # Select a match
            match = st.selectbox(
                "Match:",
                options=future_matches.loc[:, "match"],
                index=0,
                key="input_match",
                on_change=reset_inputs,
            )

            # Get teams
            home_team = future_matches.loc[
                future_matches["match"] == match, "home_team"
            ].iloc[0]
            away_team = future_matches.loc[
                future_matches["match"] == match, "away_team"
            ].iloc[0]

            auth.display_vertical_spaces(2)
            st.write(f"You are predicting:")
            st.write(f"##### {home_team} vs {away_team}")

            auth.display_vertical_spaces(2)
            # Goals difference input
            prediction = st.slider(
                "Prediction (Goals Difference):",
                min_value=-7,
                max_value=7,
                value=0,
                key="input_prediction",
            )

            # Get predictions
            predictions = auth.get_predictions()
            # Filter username
            predictions = predictions.loc[
                predictions["username"] == st.session_state.username, :
            ]
            # Filter latest
            predictions = predictions.loc[predictions["rank"] == 1, :]
            # Join usage limits with usage counts
            extra_points_usage_limits = (
                pd.DataFrame(auth.extra_points_items)
                .T.join(predictions.loc[:, "extra_points"].value_counts())
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

            auth.display_vertical_spaces(2)
            extra_points = {}
            auth.display_checkbox_group("Extra Points:")
            auth.display_vertical_spaces(1)
            with st.container(border=True):
                # Iterate over extra points items
                for k, _ in auth.extra_points_items.items():
                    extra_points[k] = st.toggle(
                        auth.extra_points_items[k]["name"],
                        value=False,
                        key=f"input_{k}",
                        on_change=manage_extra_points_inputs,
                        args=(f"input_{k}",),
                        disabled=True if extra_points_availabilities[k] == 0 else False,
                    )
                    st.caption(
                        f"""You have {"{:.0f}".format(extra_points_availabilities[k])} left"""
                    )

            # Specify which extra points item is used
            extra_points = [
                k.replace("input_", "") for k, v in extra_points.items() if v
            ]
            extra_points = None if extra_points == [] else extra_points[0]

            auth.display_vertical_spaces(2)
            # Confidence level input
            confidence_level = st.select_slider(
                "Confidence Level:",
                options=[k for k, v in auth.confidence_levels.items()],
                value=[k for k, v in auth.confidence_levels.items() if v == 0.5][0],
                key="input_confidence_level",
                help="This does not impact the score calculation, but may be displayed to others just for fun.",
            )

            auth.display_vertical_spaces(2)
            with st.expander("What does your prediction mean?", expanded=False):
                # Explain about the prediction number
                st.write(f"""Your prediction is **{prediction}**.""")
                if prediction > 0:
                    st.write(
                        f"This means you predicted that **{home_team}** will score **{prediction}** goals more than **{away_team}**."
                    )
                elif prediction == 0:
                    st.write(
                        f"This means you predicted that **{home_team}** will score the same number of goals as **{away_team}**."
                    )
                else:
                    st.write(
                        f"This means you predicted that **{home_team}** will score **{prediction*-1}** goals less than **{away_team}**."
                    )

                # Get rewarded points
                rewarded_points = auth.rewarded_points.copy()

                # Explain about the extra points items
                if extra_points == "extra_points_mult_2":
                    st.write(
                        f"""You also use **{auth.extra_points_items[extra_points]["name"]}**, which will multiply your rewarded points by the factor of 2."""
                    )
                    # Calculate example rewarded points
                    rewarded_points["Correct"] *= 2
                    rewarded_points["Correct - Tied"] *= 2
                    rewarded_points["Partial Correct"] *= 2
                    rewarded_points["Totally Wrong"] *= 2
                elif extra_points == "extra_points_add_10":
                    st.write(
                        f"""You also use **{auth.extra_points_items[extra_points]["name"]}**, which will add 10 additional points to your rewarded points. However, this will subtract 10 points from your rewarded points if your prediction is totally wrong."""
                    )
                    # Calculate example rewarded points
                    rewarded_points["Correct"] += 10
                    rewarded_points["Correct - Tied"] += 10
                    rewarded_points["Partial Correct"] += 10
                    rewarded_points["Totally Wrong"] -= 10
                # Example rewarded points
                st.write(
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

            auth.display_vertical_spaces(2)
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
                        "confidence_level": auth.confidence_levels[confidence_level],
                    }
                    # Add prediction to database
                    if auth.add_firestore_documents(
                        collection="predictions",
                        document_data=temp_prediction,
                    ):
                        # Force reset inputs on next rerun
                        st.session_state.reset_inputs = True
                        # Force display submitted dialog on next rerun
                        st.session_state.submitted = True
                        # Force clear function cache
                        auth.get_predictions.clear()
                        st.rerun()
