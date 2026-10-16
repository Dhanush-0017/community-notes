"""Settings shared by all steps, and helpers for reading the X Community Notes files."""

import glob
import os

import pandas as pd


# ---------------- input and output paths ----------------

NOTES_FILES = os.path.join("data", "notes", "notes-*.tsv")
RATINGS_FILES = os.path.join("data", "ratings", "ratings-*.tsv")
STATUS_FILES = os.path.join("data", "noteStatusHistory-*.tsv")

OUTPUT_FOLDER = os.path.join("dataset", "recent_helpful")
CACHE_FILE = os.path.join("dataset", "tweet_cache.csv")


# ---------------- dataset rules ----------------

START_DATE = "2026-10-05"   # both days are included
END_DATE = "2026-10-13"

MUST_HAVE_NOTE_ID = "2109061654621098457"   # Helpful note on the "SAUDI IS BURNING" tweet

NUMBER_OF_NOTES = 500
LANGUAGE = "en"
RANDOM_SEED = 42


# ---------------- X API ----------------

BATCH_SIZE = 100         # notes tried at a time in get_tweets.py
COST_PER_TWEET = 0.005   # US dollars


# ---------------- helpers ----------------

def find_files(name_start: str) -> list:
    """Find the files of one dataset.

    Args:
        name_start: "notes", "ratings" or "noteStatusHistory".

    Returns:
        The sorted list of file paths.
    """
    if name_start == "notes":
        pattern = NOTES_FILES
    elif name_start == "ratings":
        pattern = RATINGS_FILES
    else:
        pattern = STATUS_FILES

    files = glob.glob(pattern)
    files.sort()

    if len(files) == 0:
        raise FileNotFoundError("No files found for " + pattern)

    return files


def read_rows_for_notes(name_start: str, note_ids: set, columns: list | None = None) -> pd.DataFrame:
    """Read every file of one dataset and keep only the rows of the given notes.

    Args:
        name_start: "notes", "ratings" or "noteStatusHistory".
        note_ids: the noteIds to keep.
        columns: the columns to read. None reads all columns.

    Returns:
        A table with the matching rows from all files.
    """
    kept_parts = []

    for file in find_files(name_start):
        # The ratings files are 43 GB in total, so we read them in pieces of 1 million rows.
        chunks = pd.read_csv(
            file,
            sep="\t",
            usecols=columns,
            dtype={"noteId": str, "tweetId": str},   # as numbers, long IDs lose their last digits
            quoting=3,                                # quote marks in note text are normal text
            chunksize=1000000,
            low_memory=False,
        )

        for chunk in chunks:
            is_wanted_note = chunk["noteId"].isin(note_ids)
            wanted_rows = chunk[is_wanted_note]
            kept_parts.append(wanted_rows)

    result = pd.concat(kept_parts, ignore_index=True)
    return result
