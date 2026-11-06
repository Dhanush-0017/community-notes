"""Score the 4 Saudi notes with X's own model.

X does not publish each note's score, so this script makes it again:
    1. Read one month of ratings, up to the moment Note 4 was shown.
    2. Keep notes with 5+ ratings and raters with 10+ ratings (X's rule).
    3. Run X's model (MatrixFactorization, from github.com/twitter/communitynotes).
    4. Save each note's score and each rater's side.

The model gives every note 2 numbers:
    helpfulness_score: how much raters from all sides like the note
    one_sidedness:     how much only one side likes it (X blocks 0.5 or more)
and every rater 2 numbers:
    rater_side:        which side the rater is on (learned from who they agree with)
    rater_generosity:  how easily the rater says Helpful

Needs X's code next to this project (../communitynotes) and: pip install torch pyarrow wandb
Run:  WANDB_MODE=disabled python score_with_x_model.py
"""

import glob
import os
import sys

import pandas as pd

# X's model code
sys.path.insert(0, os.path.join("..", "communitynotes", "scoring", "src"))
from scoring.matrix_factorization.matrix_factorization import MatrixFactorization  # noqa: E402

SAUDI_FOLDER = os.path.join("dataset", "tweet_2109031558967615703")
ONE_MONTH_MS = 30 * 24 * 60 * 60 * 1000

# rater groups the Expansion model uses (from X's constants.py: Core groups + Expansion groups)
EXPANSION_MODEL_GROUPS = {1, 2, 3, 6, 8, 9, 10, 11, 13, 14, 19, 21, 25,
                          0, 4, 5, 7, 12, 15, 16, 20, 22, 23, 24, 26, 27, 28, 29, 33}

# rating -> number, same as X's process_data.py
RATING_VALUES = {"HELPFUL": 1.0, "SOMEWHAT_HELPFUL": 0.5, "NOT_HELPFUL": 0.0}


def read_last_month_of_ratings(end_ms):
    """Read every rating from the month before end_ms, by raters the Expansion model uses.

    Returns one row per rating: noteId, raterParticipantId, helpfulNum (1, 0.5 or 0).
    """
    start_ms = end_ms - ONE_MONTH_MS

    users = pd.read_csv(os.path.join("data", "userEnrollment-00000.tsv"), sep="\t",
                        usecols=["participantId", "modelingGroup"], dtype={"participantId": str})
    good_raters = set(users.loc[users["modelingGroup"].isin(EXPANSION_MODEL_GROUPS), "participantId"])

    kept = []
    for file in sorted(glob.glob(os.path.join("data", "ratings", "ratings-*.tsv"))):
        print("    reading", file)
        for chunk in pd.read_csv(file, sep="\t", chunksize=5_000_000,
                                 usecols=["noteId", "raterParticipantId", "createdAtMillis", "helpfulnessLevel"],
                                 dtype={"noteId": str, "raterParticipantId": str}):
            in_month = chunk["createdAtMillis"].between(start_ms, end_ms)
            by_good_rater = chunk["raterParticipantId"].isin(good_raters)
            kept.append(chunk[in_month & by_good_rater])
    ratings = pd.concat(kept)

    ratings["helpfulNum"] = ratings["helpfulnessLevel"].map(RATING_VALUES)
    ratings = ratings.dropna(subset=["helpfulNum"])
    return ratings[["noteId", "raterParticipantId", "helpfulNum"]]


def keep_active_notes_and_raters(ratings):
    """X's rule: notes need 5+ ratings and raters need 10+ ratings.

    Removing one can push the other under its limit, so repeat until nothing changes.
    """
    while True:
        size_before = len(ratings)

        note_counts = ratings["noteId"].value_counts()
        ratings = ratings[ratings["noteId"].isin(note_counts[note_counts >= 5].index)]

        rater_counts = ratings["raterParticipantId"].value_counts()
        ratings = ratings[ratings["raterParticipantId"].isin(rater_counts[rater_counts >= 10].index)]

        if len(ratings) == size_before:
            return ratings


def main():
    notes = pd.read_csv(os.path.join(SAUDI_FOLDER, "notes.csv"), dtype={"noteId": str})
    status = pd.read_csv(os.path.join(SAUDI_FOLDER, "note_status.csv"), dtype={"noteId": str})
    saudi_ratings = pd.read_csv(os.path.join(SAUDI_FOLDER, "ratings.csv"), dtype={"raterParticipantId": str})

    # step 1: one month of ratings, up to the moment Note 4 was shown
    note4_shown_ms = int(status.loc[status["note_label"] == "Note 4", "timestampMillisOfFirstNonNMRStatus"].iloc[0])
    print("Step 1: reading one month of ratings")
    ratings = read_last_month_of_ratings(note4_shown_ms)
    print(f"    {len(ratings):,} ratings")

    # step 2: X's 5 / 10 rule
    print("Step 2: keeping notes with 5+ ratings and raters with 10+")
    ratings = keep_active_notes_and_raters(ratings)
    print(f"    {len(ratings):,} ratings, {ratings['noteId'].nunique():,} notes, "
          f"{ratings['raterParticipantId'].nunique():,} raters")

    # step 3: X's model
    print("Step 3: running X's model (a few minutes)")
    model = MatrixFactorization(seed=42, log=False)
    note_scores, rater_scores, _ = model.run_mf(ratings)

    # step 4: save the 4 Saudi notes and the Saudi raters
    note_scores = note_scores.rename(columns={"internalNoteIntercept": "helpfulness_score",
                                              "internalNoteFactor1": "one_sidedness"})
    saudi_scores = notes[["noteId", "note_label", "writer_type"]].merge(note_scores, on="noteId")
    saudi_scores = saudi_scores.merge(status[["noteId", "currentStatus", "currentExpansionStatus"]], on="noteId")
    saudi_scores = saudi_scores[["noteId", "note_label", "writer_type", "helpfulness_score", "one_sidedness",
                                 "currentStatus", "currentExpansionStatus"]]
    saudi_scores.to_csv(os.path.join(SAUDI_FOLDER, "model_scores.csv"), index=False)
    print("Step 4: saved model_scores.csv")
    print(saudi_scores.to_string(index=False))

    rater_scores = rater_scores.rename(columns={"internalRaterIntercept": "rater_generosity",
                                                "internalRaterFactor1": "rater_side"})
    saudi_raters = rater_scores[rater_scores["raterParticipantId"].isin(saudi_ratings["raterParticipantId"])]
    saudi_raters.to_csv(os.path.join(SAUDI_FOLDER, "rater_sides.csv"), index=False)
    print(f"    saved rater_sides.csv ({len(saudi_raters)} raters)")

    # check: notes X really showed should get higher scores than notes X rejected
    all_status = pd.read_csv(os.path.join("data", "noteStatusHistory-00000.tsv"), sep="\t",
                             usecols=["noteId", "currentStatus"], dtype={"noteId": str})
    check = note_scores.merge(all_status, on="noteId")
    print("Check: average helpfulness_score by X's real decision")
    print(check.groupby("currentStatus")["helpfulness_score"].mean().round(3))


if __name__ == "__main__":
    main()
