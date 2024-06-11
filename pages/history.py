import streamlit as st

import auth

# Page config
auth.set_page_config()

if auth.get_username() is None:
    auth.display_user_login()
else:
    st.write(f"###### You are viewing as: {st.session_state.username}")
    # Get predictions
    predictions = auth.get_firestore_documents(collection="predictions")
    # Filter username
    predictions = predictions.loc[
        predictions["username"] == st.session_state.username, :
    ]
    # Convert datetime to local timezone
    predictions = predictions.astype({"timestamp": "datetime64[ns, Asia/Bangkok]"})
    # Rank by latest timestamp group by username and match
    predictions.loc[:, "rank"] = predictions.groupby(["username", "match"])["timestamp"].rank(ascending=False)
    # Create the confidence level definition column
    predictions.loc[:, "confidence_level_text"] = predictions.loc[:, "confidence_level"].map({v: k for k, v in auth.confidence_levels.items()})
    # Sort columns
    predictions = predictions.reindex(["timestamp", "match", "username", "prediction", "confidence_level", "confidence_level_text", "rank"], axis=1)
    
    # Create tabs
    tab0, tab1 = st.tabs(["Lastest", "All"])
    with tab0:
        st.dataframe(predictions.loc[predictions["rank"] == 1, :])
    with tab1:
        st.dataframe(predictions)
