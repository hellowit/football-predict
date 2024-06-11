import streamlit as st

import auth

# Page config
st.set_page_config(
    page_title="History",
    initial_sidebar_state="expanded",
)

if auth.get_username() is None:
    auth.display_user_login()
else:
    # Get predictions
    predictions = auth.get_firestore_documents(collection="predictions")
    # Filter username
    predictions = predictions.loc[
        predictions["username"] == st.session_state.username, :
    ]
    # Convert datetime to local timezone
    predictions.loc[:, "timestamp"] = predictions.loc[:, "timestamp"].dt.tz_convert(
        "Asia/Bangkok"
    )
    # Create tabs
    tab0, tab1 = st.tabs(["Latest", "All"])
    with tab1:
        st.write(predictions)
