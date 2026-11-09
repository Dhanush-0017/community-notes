"""Build a Community Notes dataset. One file makes both datasets in settings.py (DATASETS):

    helpful               500 Helpful notes written Oct 5-13, one per English tweet
    helpful_not_helpful   500 English tweets with a Helpful AND a Not Helpful note, plus a balanced file

The steps are shared:
    1. choose the notes          (choose_notes.py)
    2. get their tweets          (get_tweets.py, X API; cached tweets are free)
    3. collect their rows        (collect_data.py: Notes, Ratings, Note Status, User Enrollment)
    4. make one combined table   (tweet + note + labels + rating counts) and save it

Usage:
    python build_dataset.py helpful
    python build_dataset.py helpful_not_helpful
    add --no-tweets for a test run without the X API
"""

import os
import sys

import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from settings import DATASETS, NUMBER_OF_NOTES, RANDOM_SEED
from settings import find_files, read_rows_for_notes
from choose_notes import get_note_ids, keep_notes_in_notes_files, keep_notes_with_ratings
from choose_notes import keep_one_note_per_tweet, shuffle_notes, move_must_have_note_to_top
from get_tweets import pick_notes_with_tweets
from collect_data import filter_datasets


# ---------------- choosing notes ----------------

def find_notes_on_tweets(tweet_ids: set) -> pd.DataFrame:
    """Find every note written on the given tweets.

    Args:
        tweet_ids: the tweetIds to look for.

    Returns:
        A table with the noteId and tweetId of each note.
    """
    kept_parts = []

    for file in find_files("notes"):
        notes = pd.read_csv(file, sep="\t", usecols=["noteId", "tweetId"], dtype=str, quoting=3)
        is_on_our_tweets = notes["tweetId"].isin(tweet_ids)
        kept_parts.append(notes[is_on_our_tweets])

    all_notes = pd.concat(kept_parts, ignore_index=True)
    all_notes = all_notes.drop_duplicates("noteId")

    print("       ", len(all_notes), "notes on the", len(tweet_ids), "tweets")
    return all_notes


def keep_not_helpful_notes(all_notes: pd.DataFrame) -> pd.DataFrame:
    """Keep the notes whose status is CURRENTLY_RATED_NOT_HELPFUL.

    Args:
        all_notes: a table with noteId and tweetId columns.

    Returns:
        The Not Helpful notes (noteId, tweetId).
    """
    status = read_rows_for_notes("noteStatusHistory", set(all_notes["noteId"]), columns=["noteId", "currentStatus"])
    is_not_helpful = status["currentStatus"] == "CURRENTLY_RATED_NOT_HELPFUL"
    not_helpful_ids = set(status.loc[is_not_helpful, "noteId"])

    not_helpful = all_notes[all_notes["noteId"].isin(not_helpful_ids)]
    print("       ", len(not_helpful), "Not Helpful notes, on", not_helpful["tweetId"].nunique(), "tweets")
    return not_helpful


def order_helpful_notes(notes: pd.DataFrame, must_have_note) -> pd.DataFrame:
    """Keep one Helpful note per tweet (the one with the most ratings) and put them in random order.

    Args:
        notes: Helpful notes with noteId and tweetId.
        must_have_note: a noteId to always put first, or None.

    Returns:
        The candidate notes, in the order the tweet step should try them.
    """
    notes = keep_notes_with_ratings(notes)
    notes = keep_one_note_per_tweet(notes)
    notes = shuffle_notes(notes)

    if must_have_note is not None:
        notes = move_must_have_note_to_top(notes, must_have_note)

    return notes


def get_tweets_of(candidates: pd.DataFrame):
    """Step 2: go through the candidates until NUMBER_OF_NOTES have an English tweet that still exists.

    Args:
        candidates: the notes in the order they should be tried.

    Returns:
        chosen: the kept notes.
        tweets: one row per tweet, or None with --no-tweets.
    """
    if "--no-tweets" in sys.argv:
        print("Step 2: skipped (--no-tweets), taking the first", NUMBER_OF_NOTES, "random notes")
        return candidates.head(NUMBER_OF_NOTES), None

    print("Step 2: getting the tweets")
    return pick_notes_with_tweets(candidates)


# ---------------- the combined table ----------------

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


def make_combined(notes: pd.DataFrame, ratings: pd.DataFrame, status: pd.DataFrame, tweets) -> pd.DataFrame:
    """Join everything we know about each note into one table.

    Args:
        notes: one row per note.
        ratings: one row per rating.
        status: one row per note.
        tweets: one row per tweet, or None if the tweets were not read.

    Returns:
        One row per note with the tweet text, note text, the writer's label (classification1),
        X's status (classification2), the rating counts and the tweet information.
    """
    combined = notes[["noteId", "tweetId", "classification", "summary", "createdAtMillis", "writer_enrollmentState"]].copy()
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


def make_balanced(helpful: pd.DataFrame, not_helpful: pd.DataFrame) -> pd.DataFrame:
    """Make a balanced table: one Helpful and one Not Helpful note for every tweet.

    If a tweet has more than one Not Helpful note, the one with the most ratings is kept
    (the same rule as for the Helpful notes).

    Args:
        helpful: one Helpful note per tweet.
        not_helpful: every Not Helpful note on the same tweets.

    Returns:
        One row per note with a new first column label ("helpful" or "not_helpful"),
        the two notes of each tweet next to each other.
    """
    not_helpful = not_helpful.sort_values(["ratings_total", "noteId"], ascending=[False, True])
    one_not_helpful = not_helpful.drop_duplicates("tweetId")

    helpful = helpful.copy()
    helpful.insert(0, "label", "helpful")
    one_not_helpful = one_not_helpful.copy()
    one_not_helpful.insert(0, "label", "not_helpful")

    balanced = pd.concat([helpful, one_not_helpful], ignore_index=True)
    balanced = balanced.sort_values(["tweetId", "label"]).reset_index(drop=True)
    return balanced


# ---------------- saving ----------------

def save_csv_files(files: dict, folder: str):
    """Save each table as a CSV file in folder.

    Args:
        files: a dictionary like { "notes.csv": notes table, ... }.
        folder: where to save.
    """
    for file_name in files:
        table = files[file_name]
        table.to_csv(os.path.join(folder, file_name), index=False)
        print("        saved", file_name, "-", len(table), "rows")


def save_csv_and_excel(table: pd.DataFrame, folder: str, name: str):
    """Save one table as name.csv and name.xlsx in folder.

    Args:
        table: the table to save.
        folder: where to save.
        name: the file name without extension, e.g. "helpful".
    """
    table.to_csv(os.path.join(folder, name + ".csv"), index=False)

    # Excel can't store time zones or some hidden characters, so clean a copy first.
    excel_table = table.copy()
    for column in excel_table.columns:
        if isinstance(excel_table[column].dtype, pd.DatetimeTZDtype):
            excel_table[column] = excel_table[column].dt.tz_localize(None)
        elif excel_table[column].dtype == object:
            excel_table[column] = excel_table[column].map(
                lambda value: ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value)
    excel_table.to_excel(os.path.join(folder, name + ".xlsx"), index=False)

    print("        saved", name + ".csv and", name + ".xlsx -", len(table), "rows")


def save_readme(folder: str, lines: list):
    """Write README.md in folder.

    Args:
        folder: where to save.
        lines: the lines of the README.
    """
    with open(os.path.join(folder, "README.md"), "w") as file:
        file.write("\n".join(lines) + "\n")


FILES_AND_KEYS = [
    "## Files",
    "- tweets.csv: one row per tweet (from the X API). Key: tweetId",
    "- notes.csv: one row per note. Keys: noteId, tweetId",
    "  The writer_ columns come from the User Enrollment file (the note writer's row).",
    "  writer_enrollmentState = apiEarnedIn means the note was written by an AI note writer.",
    "- note_status.csv: one row per note. Key: noteId",
    "- ratings.csv: one row per rating. Key: noteId",
]


# ---------------- the two datasets ----------------

def build_helpful(dataset: dict):
    """500 Helpful notes, one per English tweet. Saves notes, ratings, note_status, tweets and combined."""
    # Step 1: choose the notes
    print("Step 1: choosing the notes")
    helpful_ids = get_note_ids("CURRENTLY_RATED_HELPFUL", dataset["start_date"], dataset["end_date"])
    helpful_notes = keep_notes_in_notes_files(helpful_ids)
    candidates = order_helpful_notes(helpful_notes, dataset["must_have_note"])

    # Step 2 and 3: tweets, then all rows of the chosen notes
    chosen, tweets = get_tweets_of(candidates)
    notes, ratings, status = filter_datasets(set(chosen["noteId"]))

    # Step 4: combined table and save
    combined = make_combined(notes, ratings, status, tweets)

    files = {"notes.csv": notes, "ratings.csv": ratings, "note_status.csv": status, "combined.csv": combined}
    if tweets is not None:
        files["tweets.csv"] = tweets
    save_csv_files(files, dataset["folder"])

    lines = ["# Helpful notes dataset", "",
             "Made with build_dataset.py helpful (random seed " + str(RANDOM_SEED) + ").",
             str(NUMBER_OF_NOTES) + " random notes written between " + dataset["start_date"] + " and " + dataset["end_date"] + ".",
             "Every note is rated Helpful and is in Notes, Note Status and Ratings.",
             "Every note is on a different tweet. If a tweet had more than one Helpful note,",
             "the note with the most ratings was kept.",
             "Every tweet is in English.", "",
             "Note " + str(dataset["must_have_note"]) + " (the \"SAUDI IS BURNING\" tweet) was added on purpose, not at random.", ""]
    lines += FILES_AND_KEYS
    lines += ["- combined.csv: one row per note with its tweet, both labels and rating counts", "",
              "## How the files connect",
              "- noteId connects notes, note_status, ratings and combined",
              "- tweetId connects notes and tweets", "",
              "## Limits",
              "- " + str(len(find_files("ratings"))) + " ratings files were used.",
              "- Notes whose tweet was deleted or not in English were replaced by the next random note.",
              "- Notes from the last days have fewer ratings, because people were still rating them when X made the download."]
    save_readme(dataset["folder"], lines)


def build_helpful_not_helpful(dataset: dict):
    """500 English tweets with a Helpful AND a Not Helpful note. Saves helpful, not_helpful and balanced (CSV + Excel)."""
    # Step 1: Helpful notes in the dates, kept only if their tweet also has a Not Helpful note
    print("Step 1: choosing the notes")
    helpful_ids = get_note_ids("CURRENTLY_RATED_HELPFUL", dataset["start_date"], dataset["end_date"])
    helpful_notes = keep_notes_in_notes_files(helpful_ids)

    all_notes = find_notes_on_tweets(set(helpful_notes["tweetId"]))
    not_helpful_notes = keep_not_helpful_notes(all_notes)

    has_not_helpful = helpful_notes["tweetId"].isin(not_helpful_notes["tweetId"])
    helpful_notes = helpful_notes[has_not_helpful]
    print("       ", helpful_notes["tweetId"].nunique(), "tweets have both a Helpful and a Not Helpful note")
    candidates = order_helpful_notes(helpful_notes, dataset["must_have_note"])

    # Step 2 and 3: tweets, then all rows of both kinds of notes
    chosen, tweets = get_tweets_of(candidates)
    chosen_not_helpful = not_helpful_notes[not_helpful_notes["tweetId"].isin(chosen["tweetId"])]
    notes, ratings, status = filter_datasets(set(chosen["noteId"]) | set(chosen_not_helpful["noteId"]))

    # Step 4: one combined table, split into helpful / not_helpful / balanced
    combined = make_combined(notes, ratings, status, tweets)
    helpful = combined[combined["noteId"].isin(chosen["noteId"])]
    not_helpful = combined[combined["noteId"].isin(chosen_not_helpful["noteId"])]
    balanced = make_balanced(helpful, not_helpful)

    save_csv_and_excel(helpful, dataset["folder"], "helpful")
    save_csv_and_excel(not_helpful, dataset["folder"], "not_helpful")
    save_csv_and_excel(balanced, dataset["folder"], "balanced")

    lines = ["# Helpful and Not Helpful notes on the same tweets", "",
             "Made with build_dataset.py helpful_not_helpful (random seed " + str(RANDOM_SEED) + ").",
             str(helpful["tweetId"].nunique()) + " English tweets. Each has a Helpful note written between "
             + dataset["start_date"] + " and " + dataset["end_date"] + " and at least one Not Helpful note.", "",
             "## Files (each as .csv and .xlsx, one row per note)",
             "- helpful: " + str(len(helpful)) + " notes, one per tweet (CURRENTLY_RATED_HELPFUL, the one with the most ratings)",
             "- not_helpful: " + str(len(not_helpful)) + " notes, every CURRENTLY_RATED_NOT_HELPFUL note on those tweets",
             "- balanced: " + str(len(balanced)) + " notes, one Helpful and one Not Helpful per tweet "
             "(" + str((balanced["label"] == "helpful").sum()) + " + " + str((balanced["label"] == "not_helpful").sum()) + ").",
             "  If a tweet has more than one Not Helpful note, the one with the most ratings is kept.",
             "  Column label (helpful / not_helpful) is the true answer for testing a model.", "",
             "## Main columns",
             "- tweetId: connects the two files (same tweet)",
             "- tweet_text, note_text",
             "- classification1: the writer's label (misleading or not)",
             "- classification2: X's status (currentStatus)",
             "- writer_enrollmentState: apiEarnedIn means an AI note writer",
             "- ratings_helpful, ratings_somewhat, ratings_not_helpful, ratings_total",
             "- tweet_ columns: from the X API (likes, retweets, replies, ...)", "",
             "## Limits",
             "- Only about 4 tweets a day get both kinds of notes, so the dates start on " + dataset["start_date"] + ".",
             "- Tweets that were deleted or not in English were skipped."]
    save_readme(dataset["folder"], lines)


BUILDERS = {"helpful": build_helpful, "helpful_not_helpful": build_helpful_not_helpful}


def main():
    """Read the dataset name from the command line and build it."""
    names = [argument for argument in sys.argv[1:] if not argument.startswith("--")]
    if len(names) != 1 or names[0] not in DATASETS:
        print("Usage: python build_dataset.py <name> [--no-tweets]")
        print("       name is one of:", ", ".join(DATASETS))
        return

    name = names[0]
    dataset = DATASETS[name]
    os.makedirs(dataset["folder"], exist_ok=True)

    print("Building", name, "->", dataset["folder"])
    BUILDERS[name](dataset)

    print()
    print("Done. All files are in", dataset["folder"])


if __name__ == "__main__":
    main()
