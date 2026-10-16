"""Build a dataset of 500 recent Helpful Community Notes on 500 different English tweets.

The work is done in three steps:
    Step 1 (choose_notes.py):  choose the candidate notes
    Step 2 (get_tweets.py):    get their tweets from the X API
    Step 3 (collect_data.py):  collect the Notes, Ratings and Note Status rows of the chosen notes

This file runs the steps, makes combined.csv and saves everything in OUTPUT_FOLDER.

Usage:
    python build_helpful_dataset.py               real run, uses the X API
    python build_helpful_dataset.py --no-tweets   test run, does not use the X API
"""

import os
import sys

import pandas as pd

from settings import OUTPUT_FOLDER, START_DATE, END_DATE, MUST_HAVE_NOTE_ID, NUMBER_OF_NOTES, RANDOM_SEED
from settings import find_files

from choose_notes import get_helpful_note_ids, keep_notes_in_notes_files, keep_notes_with_ratings
from choose_notes import keep_one_note_per_tweet, shuffle_notes, move_must_have_note_to_top
from get_tweets import pick_notes_with_tweets
from collect_data import filter_datasets


# ---------------- combined file ----------------

def count_ratings(ratings: pd.DataFrame) -> pd.DataFrame:
    """Count the HELPFUL, SOMEWHAT_HELPFUL and NOT_HELPFUL ratings of each note.

    Args:
        ratings: one row per rating, with noteId and helpfulnessLevel columns.

    Returns:
        One row per note with ratings_helpful, ratings_somewhat,
        ratings_not_helpful and ratings_total.
    """
    counts = {}

    for note_id, level in zip(ratings["noteId"], ratings["helpfulnessLevel"]):
        # Some old ratings have no helpfulnessLevel, so they are skipped.
        if level not in ["HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"]:
            continue

        if note_id not in counts:
            counts[note_id] = {"HELPFUL": 0, "SOMEWHAT_HELPFUL": 0, "NOT_HELPFUL": 0}

        counts[note_id][level] = counts[note_id][level] + 1

    rows = []
    for note_id in counts:
        helpful = counts[note_id]["HELPFUL"]
        somewhat = counts[note_id]["SOMEWHAT_HELPFUL"]
        not_helpful = counts[note_id]["NOT_HELPFUL"]

        row = {}
        row["noteId"] = note_id
        row["ratings_helpful"] = helpful
        row["ratings_somewhat"] = somewhat
        row["ratings_not_helpful"] = not_helpful
        row["ratings_total"] = helpful + somewhat + not_helpful
        rows.append(row)

    table = pd.DataFrame(rows)
    return table


def make_combined(notes: pd.DataFrame, ratings: pd.DataFrame, status: pd.DataFrame, tweets: pd.DataFrame | None) -> pd.DataFrame:
    """Join everything we know about each note into one table.

    Args:
        notes: one row per note.
        ratings: one row per rating.
        status: one row per note.
        tweets: one row per tweet, or None if the tweets were not read.

    Returns:
        One row per note with the tweet text, note text, the writer's label (classification1),
        the algorithm's label (classification2), the rating counts and the tweet information.
    """
    combined = notes[["noteId", "tweetId", "classification", "summary", "createdAtMillis"]].copy()
    combined = combined.rename(columns={
        "classification": "classification1",
        "summary": "note_text",
        "createdAtMillis": "note_created_at",
    })
    combined["note_created_at"] = pd.to_datetime(combined["note_created_at"], unit="ms", utc=True)

    labels = status[["noteId", "currentStatus"]]
    labels = labels.rename(columns={"currentStatus": "classification2"})
    combined = combined.merge(labels, on="noteId", how="left")

    counts = count_ratings(ratings)
    combined = combined.merge(counts, on="noteId", how="left")

    if tweets is not None:
        combined = combined.merge(tweets, on="tweetId", how="left")

        first_columns = ["noteId", "tweetId", "tweet_text", "note_text", "classification1", "classification2"]
        other_columns = []
        for column in combined.columns:
            if column not in first_columns:
                other_columns.append(column)

        combined = combined[first_columns + other_columns]

    return combined


# ---------------- saving ----------------

def save_files(files: dict):
    """Save each table as a CSV file in OUTPUT_FOLDER.

    Args:
        files: a dictionary like { "notes.csv": notes table, ... }.
    """
    for file_name in files:
        table = files[file_name]
        path = os.path.join(OUTPUT_FOLDER, file_name)
        table.to_csv(path, index=False)
        print("        saved", file_name, "-", len(table), "rows")


def save_readme():
    """Write README.md in OUTPUT_FOLDER, explaining how the dataset was made."""
    number_of_rating_files = len(find_files("ratings"))

    lines = []
    lines.append("# Helpful notes dataset")
    lines.append("")
    lines.append("Made with build_helpful_dataset.py (random seed " + str(RANDOM_SEED) + ").")
    lines.append(str(NUMBER_OF_NOTES) + " random notes written between " + START_DATE + " and " + END_DATE + ".")
    lines.append("Every note is rated Helpful and is in Notes, Note Status and Ratings.")
    lines.append("Every note is on a different tweet. If a tweet had more than one Helpful note,")
    lines.append("the note with the most ratings was kept.")
    lines.append("Every tweet is in English.")
    lines.append("")
    lines.append("Note " + MUST_HAVE_NOTE_ID + " (the \"SAUDI IS BURNING\" tweet) was added on purpose, not at random.")
    lines.append("")
    lines.append("## Files")
    lines.append("- tweets.csv: one row per tweet (from the X API). Key: tweetId")
    lines.append("- notes.csv: one row per note. Keys: noteId, tweetId")
    lines.append("- note_status.csv: one row per note. Key: noteId")
    lines.append("- ratings.csv: one row per rating. Key: noteId")
    lines.append("- combined.csv: one row per note with its tweet, both labels and rating counts")
    lines.append("")
    lines.append("## How the files connect")
    lines.append("- noteId connects notes, note_status, ratings and combined")
    lines.append("- tweetId connects notes and tweets")
    lines.append("")
    lines.append("## Limits")
    lines.append("- " + str(number_of_rating_files) + " ratings files were used.")
    lines.append("- Notes whose tweet was deleted or not in English were replaced by the next random note.")
    lines.append("- Notes from the last days have fewer ratings, because people were still rating them when X made the download.")

    path = os.path.join(OUTPUT_FOLDER, "README.md")
    with open(path, "w") as file:
        file.write("\n".join(lines) + "\n")


# ---------------- main ----------------

def main():
    """Run the three steps, make the combined file and save everything."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Step 1: choose the candidate notes
    helpful_ids = get_helpful_note_ids()
    notes = keep_notes_in_notes_files(helpful_ids)
    common = keep_notes_with_ratings(notes)
    one_per_tweet = keep_one_note_per_tweet(common)
    candidates = shuffle_notes(one_per_tweet)
    candidates = move_must_have_note_to_top(candidates)

    if len(candidates) < NUMBER_OF_NOTES:
        print("Not enough notes:", len(candidates), "found, but", NUMBER_OF_NOTES, "needed")
        return

    # Step 2: get the tweets
    if "--no-tweets" in sys.argv:
        print("Step 2: skipped (--no-tweets), taking the first", NUMBER_OF_NOTES, "random notes")
        chosen = candidates.head(NUMBER_OF_NOTES)
        tweets = None
    else:
        chosen, tweets = pick_notes_with_tweets(candidates)

    # Step 3: collect all rows of the chosen notes
    chosen_ids = set(chosen["noteId"])
    notes, ratings, status = filter_datasets(chosen_ids)

    combined = make_combined(notes, ratings, status, tweets)

    files = {}
    files["notes.csv"] = notes
    files["ratings.csv"] = ratings
    files["note_status.csv"] = status
    files["combined.csv"] = combined
    if tweets is not None:
        files["tweets.csv"] = tweets

    save_files(files)
    save_readme()

    print()
    print("Done. All files are in", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
