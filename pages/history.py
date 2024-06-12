import streamlit as st

import auth

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"You are viewing as: **{st.session_state.username}**")
    # Matrics
    col0, col1, col2 = st.columns(3)
    col0.metric("Rank", "2", "1")
    col1.metric("Total Score", "35", "3")
    col2.metric("% Accuracy", "99%", "-8%")
    # Get predictions
    predictions = auth.get_predictions()
    # Filter username
    predictions = predictions.loc[
        predictions["username"] == st.session_state.username, :
    ]
    # Create tabs
    tab0, tab1 = st.tabs(["Latest", "All"])
    with tab0:
        st.dataframe(predictions.loc[predictions["rank"] == 1, :])
    with tab1:
        st.dataframe(predictions)
