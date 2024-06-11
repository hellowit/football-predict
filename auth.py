import streamlit as st
from streamlit_gsheets import GSheetsConnection

import pandas as pd
import time

from google.cloud import firestore
import json

# Awarded points config
awarded_points = {
    "All Correct": 3,
    "Partial Correct": 1,
    "All Wrong": 0,
    "Penalty": -0.75,
}

# Confidence levels config
confidence_levels = {
    "I'm always wrong": 0,
    "No so good at this": 0.25,
    "No better than flipping a coin": 0.5,
    "Somewhat confident": 0.75,
    "I can see the future!": 1,
}

def set_page_config():
    # Page config
    st.set_page_config(
        page_title="football-predict",
        page_icon="⚽",
        initial_sidebar_state="expanded",
    )

@st.experimental_dialog("Assistant", )
def display_assistant():
    with st.container(height=200):
        if prompt := st.chat_input():
            st.chat_message("human").write(prompt)


def get_firestore_database():
    db = firestore.Client.from_service_account_info(json.loads(st.secrets["textkey"]))
    return db


def get_firestore_documents(collection):
    database = get_firestore_database()
    df = pd.DataFrame(
        [document.to_dict() for document in database.collection(collection).stream()]
    )
    return df


def add_firestore_documents(collection, document_data, id=None, merge=True):
    database = get_firestore_database()
    database.collection(collection).document(id).set(
        document_data,
        merge=merge,
    )
    return True


def get_data_gsheets(worksheet, usecols, ttl=60):
    # Connect to Google sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Get worksheet
    df = conn.read(worksheet=worksheet, usecols=usecols, ttl=ttl).dropna(how="all")
    return df


def update_data_gsheets(worksheet, data):
    # Connect to Google sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Update worksheet
    df = conn.update(worksheet=worksheet, data=data)
    return True


def get_username():
    if "username" not in st.session_state:
        st.session_state.username = None
    return st.session_state.username


def display_checkbox_group(text):
    st.markdown(
        f"""
        <label aria-hidden='true' class='st-emotion-cache-1jmvea6 e1nzilvr4'>
            <div data-testid='stMarkdownContainer' class='css-16idsys e16nr0p34'>
                <p>{text}</p>
            </div>
        </label>
        """,
        unsafe_allow_html=True,
    )


def display_vertical_spaces(rows):
    for _ in range(rows):
        st.write("")


def display_user_login():
    # SecurityKey list
    securitykey_list = [
        "Avocado",
        "Banana",
        "Lychee",
        "Melon",
        "Orange",
        "Pineapple",
    ]

    # Create tabs
    tab0, tab1 = st.tabs(["Login", "Register"])
    with tab0:
        with st.form(key="login"):
            # Get users
            # users = get_data_gsheets(worksheet="users", usecols=list(range(2)), ttl=60)
            users = get_firestore_documents(collection="users")
            # Username selection
            input_username = st.selectbox(
                "Username:",
                options=users.loc[:, "username"],
                index=None,
                key="input_username",
            )

            # SecurityKey checkboxes
            input_securitykey = {}
            display_checkbox_group("SecurityKey:")
            for key in securitykey_list:
                input_securitykey[key] = st.checkbox(
                    key,
                    key=f"securitykey_{key}",
                )

            # Login button
            if st.form_submit_button(
                "Login",
                type="primary",
            ):
                with st.spinner("Processing..."):
                    if len(input_username) > 0:
                        temp_securitykey = ", ".join(
                            [k for k, v in input_securitykey.items() if v]
                        )
                        if (
                            temp_securitykey
                            == users.loc[
                                users["username"] == input_username, "password"
                            ].iloc[0]
                        ):
                            st.session_state.username = input_username
                            st.rerun()
                        else:
                            st.error("Invalid SecurityKey!")
                    else:
                        st.error("Invalid Username")
    with tab1:
        with st.form(key="register"):
            # Username
            reg_username = st.text_input(
                "Username:",
                max_chars=20,
                key="reg_username",
            )
            # SecurityKey checkboxes
            reg_securitykey = {}
            display_checkbox_group("SecurityKey:")
            st.caption("Please do not forget your SecurityKey!")
            for key in securitykey_list:
                reg_securitykey[key] = st.checkbox(
                    key,
                    key=f"reg_securitykey_{key}",
                )

            # Register button
            if st.form_submit_button(
                "Register",
                type="primary",
            ):
                with st.spinner("Processing..."):
                    temp_securitykey = ", ".join(
                        [k for k, v in reg_securitykey.items() if v]
                    )
                    if len(reg_username) >= 3 and temp_securitykey != "":
                        # Get users
                        # users = get_data_gsheets(
                        #     worksheet="users", usecols=list(range(2)), ttl=0
                        # )
                        users = get_firestore_documents(collection="users")
                        if users.loc[:, "username"].str.contains(reg_username).any():
                            st.error("This username is not available!")
                        else:
                            # temp_user = pd.DataFrame(
                            #     [
                            #         {
                            #             "username": reg_username,
                            #             "password": temp_securitykey,
                            #         }
                            #     ]
                            # )
                            # updated_users = pd.concat(
                            #     [users, temp_user], ignore_index=True
                            # )
                            # if update_data_gsheets("users", updated_users):
                            temp_user = {
                                "username": reg_username,
                                "password": temp_securitykey,
                            }
                            if add_firestore_documents(
                                collection="users",
                                document_data=temp_user,
                                id=reg_username,
                            ):
                                st.success("Registration completed!")
                                st.balloons()
                                st.warning("Redirecting to home...")
                                time.sleep(2.5)
                                st.session_state.username = reg_username
                                st.rerun()

                    else:
                        st.error("Username must be 3 characters or more!")
