import auth
import pandas as pd


def get_matches():
    # Get matches
    matches = auth.get_data_gsheets(worksheet="matches", usecols=list(range(8)))
    # Convert datetime to local timezone
    matches = matches.astype({"datetime": "datetime64[ns, Asia/Bangkok]"})
    return matches


def get_predictions():
    # Get predictions
    predictions = auth.get_firestore_documents(collection="predictions")
    # Convert datetime to local timezone
    predictions = predictions.astype({"timestamp": "datetime64[ns, Asia/Bangkok]"})
    # Create a confidence level definition column
    predictions.loc[:, "confidence_level_text"] = predictions.loc[
        :, "confidence_level"
    ].map({v: k for k, v in auth.confidence_levels.items()})

    # # Sort columns
    # predictions = predictions.reindex(
    #     [
    #         "timestamp",
    #         "match",
    #         "username",
    #         "prediction",
    #         "confidence_level",
    #         "confidence_level_text",
    #         "rank",
    #     ],
    #     axis=1,
    # )

    # Get matches
    matches = get_matches()
    # Drop other columns
    matches = matches.loc[:, ["datetime", "match"]]

    # Merge predictions with matches
    valid_predictions = predictions.merge(
        matches,
        how="inner",
        left_on="match",
        right_on="match",
    )
    # Drop predictions, if submitted after the match is started
    valid_predictions = valid_predictions.loc[
        valid_predictions["timestamp"] <= valid_predictions["datetime"], :
    ]

    # Rank by latest timestamp group by username and match
    valid_predictions.loc[:, "rank"] = valid_predictions.groupby(["username", "match"])[
        "timestamp"
    ].rank(ascending=False)

    # Sort columns by name
    valid_predictions = valid_predictions.reindex(
        sorted(valid_predictions.columns), axis=1
    )

    return valid_predictions


print(get_predictions().sort_values(["match", "username", "rank"]))
