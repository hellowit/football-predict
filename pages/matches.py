import streamlit as st

import auth

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    # Get matches
    matches = auth.get_data_gsheets(
        worksheet="matches", usecols=list(range(8))
    )
    st.write(matches)   