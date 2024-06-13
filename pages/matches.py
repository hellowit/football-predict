import streamlit as st

import auth

import numpy as np
import pandas as pd

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"You are viewing as: **{st.session_state.username}**")
    # Get matches
    matches = auth.get_future_matches(12)
    matches = matches.sort_values("datetime")
    for i in range(matches.shape[0]):
        with st.container(border=True):
            st.markdown(f"""###### {matches.loc[matches.index[i], "match"]}""")
            st.markdown(f"""##### {matches.loc[matches.index[i], "home_team"]} - {matches.loc[matches.index[i], "away_team"]}""")
            if matches.loc[matches.index[i], "goals_difference"] is not np.nan:
                st.markdown(f"""#### {"{:.0f}".format(matches.loc[matches.index[i], "home_goals"])} - {"{:.0f}".format(matches.loc[matches.index[i], "away_goals"])}""")