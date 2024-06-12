import streamlit as st

import auth

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"You are viewing as: **{st.session_state.username}**")
    # Get matches
    matches = auth.get_matches()
    st.write(matches)