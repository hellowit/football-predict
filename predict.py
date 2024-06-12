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
    st.session_state.reset_inputs = False


def adjust_goal(*args):
    st.session_state.input_prediction += args[0]


# Page config
auth.set_page_config()

if "reset_inputs" not in st.session_state:
    st.session_state.reset_inputs = False

if st.session_state.reset_inputs:
    reset_inputs()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"###### You are viewing as: {st.session_state.username}")

    auth.display_vertical_spaces(2)
    # Matrics
    col0, col1, col2 = st.columns(3)
    col0.metric("Rank", "2", "1")
    col1.metric("Total Score", "35", "3")
    col2.metric("% Accuracy", "99%", "-8%")

    auth.display_vertical_spaces(2)
    # Create tabs
    (tab0,) = st.tabs(["New Prediction"])
    with tab0:
        # Get matches
        future_matches = auth.get_data_gsheets(
            worksheet="matches", usecols=list(range(8))
        )
        # Filter for top 3 future matches only
        future_matches = future_matches.loc[
            future_matches["is_future_match"] == True, :
        ].iloc[:3, :]

        # Check if there is any available future matches
        if future_matches.shape[0] == 0:
            st.write("There is no more matches to predict!")
        else:
            # Select a match
            match = st.selectbox(
                "Match:",
                options=future_matches.loc[:, "match"],
                index=0,
                on_change=reset_inputs,
            )

            # Get teams
            home_team = future_matches.loc[
                future_matches["match"] == match, "home"
            ].iloc[0]
            away_team = future_matches.loc[
                future_matches["match"] == match, "away"
            ].iloc[0]

            auth.display_vertical_spaces(2)
            st.write(f"##### You are predicting: {home_team} vs {away_team}")

            auth.display_vertical_spaces(2)
            prediction = st.slider(
                "Prediction (Goals Difference):",
                min_value=-7,
                max_value=7,
                value=0,
                key="input_prediction",
            )

            # Align right on 2nd column
            # st.markdown(
            #     """
            #     <style>
            #         div[data-testid='column']:nth-of-type(2)
            #         {
            #             text-align: end;
            #         }
            #     </style>
            #     """,
            #     unsafe_allow_html=True,
            # )
            # Create column
            # col0, col1 = st.columns(2)
            # with col0:
            #     st.button(
            #         f"{away_team}",
            #         key="input_minus_goal",
            #         on_click=adjust_goal,
            #         args=[-1],
            #     )
            # with col1:
            #     st.button(
            #         f"{home_team}",
            #         key="input_plus_goal",
            #         on_click=adjust_goal,
            #         args=[1],
            #     )

            auth.display_vertical_spaces(2)
            confidence_level = st.select_slider(
                "Confidence Level:",
                options=[k for k, v in auth.confidence_levels.items()],
                value=[k for k, v in auth.confidence_levels.items() if v == 0.5][0],
                key="input_confidence_level",
                help="This does not impact the score calculation, but may be displayed to others just for fun.",
            )

            # # Vertical spaces
            # auth.display_vertical_spaces(2)
            # multipler = st.slider(
            #     "Multiplier:",
            #     min_value=1.0,
            #     max_value=2.0,
            #     value=1.0,
            #     step=0.25,
            # )

            # with st.expander("How does a multiplier affect your score?", expanded=False):
            #     # st.write(
            #     #     """With a multiplier of 1:
            #     #          You will get 3 points, if predicted correctly.
            #     #          You will get 1 point, if predicted the correct winning teams, but wrong goals difference.
            #     #          You will get 0 point, if predicted wrongly.  """
            #     # )
            #     st.write(
            #         f"""
            #         After taking into accout your selected multiplier, points will be awarded as below:

            #         |Outcome|Points|
            #         |---|---|
            #         |Correct goals difference|{auth.awarded_points["All Correct"] * multipler}|
            #         |Correct winning team, but wrong goals difference|{auth.awarded_points["Partial Correct"] * multipler}|
            #         |All wrong|{auth.awarded_points["Penalty"] * multipler}|
            #         """
            #     )
            #     auth.display_vertical_spaces(1)

            auth.display_vertical_spaces(2)
            with st.expander("What does your prediction mean?", expanded=False):
                st.write(f"""Your prediction is **{prediction}**.""")
                if prediction > 0:
                    st.write(
                        f"This means your predicted that **{home_team}** will score **{prediction}** goals more than **{away_team}**."
                    )
                elif prediction == 0:
                    st.write(
                        f"This means your predicted that **{home_team}** will score the same number of goals as **{away_team}**."
                    )
                else:
                    st.write(
                        f"This means your predicted that **{home_team}** will score **{prediction*-1}** goals less than **{away_team}**."
                    )
                st.write(
                    f"""
                    Points will be awarded as below:
                    
                    |Outcome|Points|
                    |---|---|
                    |Correct goals difference|{auth.awarded_points["All Correct"]}|
                    |Correct winning team, but wrong goals difference|{auth.awarded_points["Partial Correct"]}|
                    |All wrong|{auth.awarded_points["All Wrong"]}|
                    """
                )
                auth.display_vertical_spaces(1)

            auth.display_vertical_spaces(2)
            if st.button(
                "Submit",
                type="primary",
            ):
                with st.spinner():
                    # Get predictions
                    # predictions = auth.get_data_gsheets(
                    #     worksheet="predictions", usecols=list(range(4)), ttl=0
                    # )
                    # temp_prediction = pd.DataFrame(
                    #     [
                    #         {
                    #             "datetime": dt.datetime.today().astimezone(tz=dt.timezone(dt.timedelta(hours=7))).isoformat(),
                    #             "username": st.session_state.username,
                    #             "prediction": prediction,
                    #             "confidence_level": confidence_levels[confidence_level],
                    #         }
                    #     ]
                    # )
                    # updated_predicions = pd.concat(
                    #     [predictions, temp_prediction], ignore_index=True
                    # )
                    # if auth.update_data_gsheets("predictions", updated_predicions):
                    # Create prediction dict
                    temp_prediction = {
                        "timestamp": dt.datetime.today().astimezone(
                            tz=dt.timezone(dt.timedelta(hours=7))
                        ),
                        "username": st.session_state.username,
                        "match": match,
                        "prediction": prediction,
                        "confidence_level": auth.confidence_levels[confidence_level],
                    }
                    # Add prediction to database
                    if auth.add_firestore_documents(
                        collection="predictions",
                        document_data=temp_prediction,
                    ):
                        st.success("Prediction submitted!")
                        st.balloons()
                        # Reset after rerun
                        st.session_state.reset_inputs = True
                        st.rerun()
