import streamlit as st

import auth

import numpy as np
import pandas as pd
import datetime as dt
import time

# Page config
st.set_page_config(
    page_title="Predict",
    initial_sidebar_state="expanded",
)


def reset_inputs():
    st.session_state.input_prediction = 0
    st.session_state.input_confidence_level = [
        k for k, v in confidence_levels.items() if v == 0.5
    ][0]


@st.experimental_dialog("Prediction Reciept")
def display_prediction_reciept(prediction):
    st.write("SDFSDF")
    st.download_button(
        "Download Reciept",
        data=prediction.to_json(orient="records"),
        file_name="rrr.txt",
    )


if auth.get_username() is None:
    auth.display_user_login()
else:
    st.header("Predict Euro 2024")
    st.subheader(f"Hi {st.session_state.username}!")

    auth.display_vertical_spaces(2)
    # Matrics
    col0, col1, col2 = st.columns(3)
    col0.metric("Rank", "2", "1")
    col1.metric("Total Score", "35", "3")
    col2.metric("% Accuracy", "99%", "-8%")

    auth.display_vertical_spaces(2)
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

            home_team = future_matches.loc[
                future_matches["match"] == match, "home"
            ].iloc[0]
            away_team = future_matches.loc[
                future_matches["match"] == match, "away"
            ].iloc[0]

            # Vertical spaces
            auth.display_vertical_spaces(2)
            st.subheader(f"{home_team} vs {away_team}")

            # Vertical spaces
            auth.display_vertical_spaces(2)
            prediction = st.slider(
                "Prediction:",
                min_value=-10,
                max_value=10,
                value=0,
                key="input_prediction",
                help="Goals difference",
            )

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

            # Confidence levels
            confidence_levels = {
                "I'm always wrong": 0,
                "No so good at this": 0.25,
                "No better than flipping a coin": 0.5,
                "Somewhat confident": 0.75,
                "I can see the future!": 1,
            }

            auth.display_vertical_spaces(2)
            confidence_level = st.select_slider(
                "Confidence Level:",
                options=[k for k, v in confidence_levels.items()],
                value=[k for k, v in confidence_levels.items() if v == 0.5][0],
                key="input_confidence_level",
                help="Do not have an impact on the score calculation.",
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
                    temp_prediction = {
                        "timestamp": dt.datetime.today()
                        .astimezone(tz=dt.timezone(dt.timedelta(hours=7))),
                        "username": st.session_state.username,
                        "match": match,
                        "prediction": prediction,
                        "confidence_level": confidence_levels[confidence_level],
                    }
                    if auth.add_firestore_documents(
                        collection="predictions",
                        document_data=temp_prediction,
                    ):
                        st.success("Prediction submitted!")
