"""Score the 4 Saudi notes with X's own matrix factorization model.

X does not publish each note's score, so this script recreates it:
    1. Take one month of ratings, up to the moment Note 4 was shown, from raters in the
       Core and Expansion groups (the raters the Expansion model uses).
    2. Apply X's filters: notes need 5+ ratings, raters need 10+ ratings.
    3. Fit X's MatrixFactorization class (from github.com/twitter/communitynotes).
    4. Save each note's helpfulness score (intercept) and one-sidedness (factor), and
       each Saudi rater's side (factor).

Needs a copy of X's repository next to this project (../communitynotes) and the packages
torch, pyarrow and wandb (pip install torch pyarrow wandb).

Usage:
    WANDB_MODE=disabled python score_with_x_model.py
"""

import glob
import os
import sys

import pandas as pd

X_REPO = os.path.join("..", "communitynotes", "scoring", "src")
sys.path.insert(0, X_REPO)
from scoring.matrix_factorization.matrix_factorization import MatrixFactorization  # noqa: E402

SAUDI_FOLDER = os.path.join("dataset", "tweet_2109031558967615703")
DAYS_OF_RATINGS = 30

# group lists from X's code: scoring/src/scoring/constants.py
CORE_GROUPS = {1, 2, 3, 6, 8, 9, 10, 11, 13, 14, 19, 21, 25}
EXPANSION_GROUPS = {0, 4, 5, 7, 12, 15, 16, 20, 22, 23, 24, 26, 27, 28, 29, 33}


def load_window_ratings(end_millis: int) -> pd.DataFrame:
    """Read one month of ratings before end_millis, from raters the Expansion model uses.

    Args:
        end_millis: the last moment to include, in milliseconds.

    Returns:
        One row per rating with noteId, raterParticipantId and helpfulNum (1, 0.5 or 0).
    """
    start_millis = end_millis - DAYS_OF_RATINGS * 24 * 60 * 60 * 1000

    users = pd.read_csv(os.path.join("data", "userEnrollment-00000.tsv"), sep="\t",
                        usecols=["participantId", "modelingGroup"], dtype={"participantId": str})
    is_expansion_rater = users["modelingGroup"].isin(CORE_GROUPS | EXPANSION_GROUPS)
    expansion_raters = set(users.loc[is_expansion_rater, "participantId"])

    kept_parts = []
    columns = ["noteId", "raterParticipantId", "createdAtMillis", "helpfulnessLevel", "helpful", "notHelpful"]
    for file in sorted(glob.glob(os.path.join("data", "ratings", "ratings-*.tsv"))):
        print("    reading", file)
        for chunk in pd.read_csv(file, sep="\t", usecols=columns, chunksize=5_000_000,
                                 dtype={"noteId": str, "raterParticipantId": str}):
            in_window = (chunk["createdAtMillis"] >= start_millis) & (chunk["createdAtMillis"] <= end_millis)
            by_expansion_rater = chunk["raterParticipantId"].isin(expansion_raters)
            kept_parts.append(chunk[in_window & by_expansion_rater])
    ratings = pd.concat(kept_parts)

    # same rating values as X's process_data.py
    ratings["helpfulNum"] = float("nan")
    ratings.loc[ratings["helpful"] == 1, "helpfulNum"] = 1.0
    ratings.loc[ratings["notHelpful"] == 1, "helpfulNum"] = 0.0
    ratings.loc[ratings["helpfulnessLevel"] == "HELPFUL", "helpfulNum"] = 1.0
    ratings.loc[ratings["helpfulnessLevel"] == "SOMEWHAT_HELPFUL", "helpfulNum"] = 0.5
    ratings.loc[ratings["helpfulnessLevel"] == "NOT_HELPFUL", "helpfulNum"] = 0.0
    ratings = ratings.dropna(subset=["helpfulNum"])

    return ratings[["noteId", "raterParticipantId", "helpfulNum"]]


def apply_x_filters(ratings: pd.DataFrame) -> pd.DataFrame:
    """Keep notes with 5+ ratings and raters with 10+ ratings, repeating until nothing changes.

    Args:
        ratings: one row per rating.

    Returns:
        The ratings that pass X's prescoring filters.
    """
    while True:
        size_before = len(ratings)

        ratings_per_note = ratings.groupby("noteId").size()
        notes_to_keep = ratings_per_note[ratings_per_note >= 5].index
        ratings = ratings[ratings["noteId"].isin(notes_to_keep)]

        ratings_per_rater = ratings.groupby("raterParticipantId").size()
        raters_to_keep = ratings_per_rater[ratings_per_rater >= 10].index
        ratings = ratings[ratings["raterParticipantId"].isin(raters_to_keep)]

        if len(ratings) == size_before:
            return ratings


def main():
    """Fit X's model on the month of ratings and save the Saudi notes' scores."""
    notes = pd.read_csv(os.path.join(SAUDI_FOLDER, "notes.csv"), dtype={"noteId": str})
    status = pd.read_csv(os.path.join(SAUDI_FOLDER, "note_status.csv"), dtype={"noteId": str})
    saudi_ratings = pd.read_csv(os.path.join(SAUDI_FOLDER, "ratings.csv"), dtype={"raterParticipantId": str})

    is_note_4 = status["note_label"] == "Note 4"
    note_4_shown_millis = int(status.loc[is_note_4, "timestampMillisOfFirstNonNMRStatus"].iloc[0])

    print("Step 1: one month of ratings before Note 4 was shown")
    ratings = load_window_ratings(note_4_shown_millis)
    print(f"    {len(ratings):,} ratings")

    print("Step 2: X's filters (notes 5+ ratings, raters 10+ ratings)")
    ratings = apply_x_filters(ratings)
    print(f"    {len(ratings):,} ratings, {ratings['noteId'].nunique():,} notes, {ratings['raterParticipantId'].nunique():,} raters")

    print("Step 3: fitting X's matrix factorization model")
    model = MatrixFactorization(seed=42, log=False)
    note_params, rater_params, global_intercept = model.run_mf(ratings)
    print(f"    done, global intercept {global_intercept:.3f}")

    print("Step 4: saving the results")
    note_params = note_params.rename(columns={"internalNoteIntercept": "helpfulness_score",
                                              "internalNoteFactor1": "one_sidedness"})
    saudi_scores = notes[["noteId", "note_label", "writer_type"]].merge(
        note_params[["noteId", "helpfulness_score", "one_sidedness"]], on="noteId")
    saudi_scores = saudi_scores.merge(status[["noteId", "currentStatus", "currentExpansionStatus"]], on="noteId")
    saudi_scores.to_csv(os.path.join(SAUDI_FOLDER, "model_scores.csv"), index=False)
    print(saudi_scores.to_string(index=False))

    rater_params = rater_params.rename(columns={"internalRaterIntercept": "rater_generosity",
                                                "internalRaterFactor1": "rater_side"})
    saudi_rater_ids = set(saudi_ratings["raterParticipantId"])
    saudi_raters = rater_params[rater_params["raterParticipantId"].isin(saudi_rater_ids)]
    saudi_raters.to_csv(os.path.join(SAUDI_FOLDER, "rater_sides.csv"), index=False)
    print(f"    sides saved for {len(saudi_raters)} of {len(saudi_rater_ids)} Saudi raters")

    # check: do notes X really showed get higher scores in our model?
    all_status = pd.read_csv(os.path.join("data", "noteStatusHistory-00000.tsv"), sep="\t",
                             usecols=["noteId", "currentStatus"], dtype={"noteId": str})
    check = note_params.merge(all_status, on="noteId")
    print("Check: average score by X's real status")
    print(check.groupby("currentStatus")["helpfulness_score"].agg(["count", "mean"]).round(3))


if __name__ == "__main__":
    main()
