import streamlit as st

import auth

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    # st.write(f"You are viewing as: **{st.session_state.username}**")
    if st.button(f"You are viewing as: **{st.session_state.username}**"):
        st.cache_data.clear()

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
