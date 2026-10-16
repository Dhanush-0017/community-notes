"""Step 1: choose the candidate notes.

A candidate is a Helpful note written between START_DATE and END_DATE that is in
Notes, Note Status and Ratings. Each tweet keeps only one note.
"""

import pandas as pd

from settings import START_DATE, END_DATE, MUST_HAVE_NOTE_ID, RANDOM_SEED
from settings import find_files, read_rows_for_notes


def get_helpful_note_ids() -> set:
    """Find the Helpful notes written between START_DATE and END_DATE.

    Returns:
        A set of noteIds.
    """
    status_file = find_files("noteStatusHistory")[0]
    status = pd.read_csv(
        status_file,
        sep="\t",
        usecols=["noteId", "createdAtMillis", "currentStatus"],
        dtype={"noteId": str},
    )

    is_helpful = status["currentStatus"] == "CURRENTLY_RATED_HELPFUL"
    helpful_rows = status[is_helpful]
    print("Step 1:", len(helpful_rows), "Helpful notes in Note Status")

    # createdAtMillis is in milliseconds, so turn it into a day like "2026-10-05"
    # that can be compared with START_DATE and END_DATE.
    note_times = pd.to_datetime(helpful_rows["createdAtMillis"], unit="ms", utc=True)
    note_days = note_times.dt.strftime("%Y-%m-%d")

    is_on_or_after_start = note_days >= START_DATE
    is_on_or_before_end = note_days <= END_DATE
    is_in_date_range = is_on_or_after_start & is_on_or_before_end
    helpful_rows = helpful_rows[is_in_date_range]

    helpful_ids = set(helpful_rows["noteId"])

    print("       ", len(helpful_ids), "of them were written between", START_DATE, "and", END_DATE)
    return helpful_ids


def keep_notes_in_notes_files(helpful_ids: set) -> pd.DataFrame:
    """Find the notes in the Notes files.

    Args:
        helpful_ids: the noteIds to look for.

    Returns:
        A table with the noteId and tweetId of each note that was found.
    """
    notes = read_rows_for_notes("notes", helpful_ids, columns=["noteId", "tweetId"])
    notes = notes.drop_duplicates("noteId")

    print("       ", len(notes), "of them are in Notes")
    return notes


def keep_notes_with_ratings(notes: pd.DataFrame) -> pd.DataFrame:
    """Keep the notes that have at least one rating, and count their ratings.

    Args:
        notes: a table with a noteId column.

    Returns:
        The notes that have ratings, with a new column "number_of_ratings".
    """
    note_ids = set(notes["noteId"])
    rating_counts = {}

    for file in find_files("ratings"):
        print("        counting ratings in", file)

        # Only the noteId column is needed here, which makes reading 43 GB much faster.
        chunks = pd.read_csv(
            file,
            sep="\t",
            usecols=["noteId"],
            dtype={"noteId": str},
            chunksize=3000000,
        )

        for chunk in chunks:
            is_our_note = chunk["noteId"].isin(note_ids)
            our_rows = chunk[is_our_note]

            for note_id in our_rows["noteId"]:
                if note_id in rating_counts:
                    rating_counts[note_id] = rating_counts[note_id] + 1
                else:
                    rating_counts[note_id] = 1

    rated_ids = list(rating_counts.keys())
    has_ratings = notes["noteId"].isin(rated_ids)
    common = notes[has_ratings].copy()

    number_of_ratings = []
    for note_id in common["noteId"]:
        number_of_ratings.append(rating_counts[note_id])
    common["number_of_ratings"] = number_of_ratings

    print("       ", len(common), "of them also have Ratings (common in all 3 datasets)")
    return common


def keep_one_note_per_tweet(notes: pd.DataFrame) -> pd.DataFrame:
    """Keep one note per tweet: the note with the most ratings.

    If two notes have the same number of ratings, the older note is kept.

    Args:
        notes: a table with noteId, tweetId and number_of_ratings columns.

    Returns:
        A table with one note per tweet.
    """
    best_note_of_tweet = {}

    for index, note in notes.iterrows():
        tweet_id = note["tweetId"]

        if tweet_id not in best_note_of_tweet:
            best_note_of_tweet[tweet_id] = note
            continue

        best_so_far = best_note_of_tweet[tweet_id]

        if note["number_of_ratings"] > best_so_far["number_of_ratings"]:
            best_note_of_tweet[tweet_id] = note
        elif note["number_of_ratings"] == best_so_far["number_of_ratings"]:
            # X gives IDs in time order, so a smaller noteId means an older note.
            if int(note["noteId"]) < int(best_so_far["noteId"]):
                best_note_of_tweet[tweet_id] = note

    kept_notes = []
    for tweet_id in best_note_of_tweet:
        kept_notes.append(best_note_of_tweet[tweet_id])

    result = pd.DataFrame(kept_notes)

    print("       ", len(result), "different tweets (kept the note with the most ratings for each tweet)")
    return result


def shuffle_notes(notes: pd.DataFrame) -> pd.DataFrame:
    """Put the notes in a random order that is the same on every run.

    Args:
        notes: a table with a noteId column.

    Returns:
        The same notes in a random order.
    """
    # Sorting first makes the starting order fixed, so the seed always gives the same shuffle.
    notes = notes.sort_values("noteId")
    notes = notes.sample(frac=1, random_state=RANDOM_SEED)   # frac=1 keeps all rows
    notes = notes.reset_index(drop=True)
    return notes


def move_must_have_note_to_top(notes: pd.DataFrame) -> pd.DataFrame:
    """Move MUST_HAVE_NOTE_ID to the first row, so step 2 always chooses it.

    Args:
        notes: a table with a noteId column.

    Returns:
        The same notes with the must-have note first.
    """
    is_must_have = notes["noteId"] == MUST_HAVE_NOTE_ID
    must_have_row = notes[is_must_have]

    if len(must_have_row) == 0:
        print("  Warning: the must-have note", MUST_HAVE_NOTE_ID, "is not in the list of notes")
        return notes

    is_other_note = notes["noteId"] != MUST_HAVE_NOTE_ID
    other_rows = notes[is_other_note]

    notes = pd.concat([must_have_row, other_rows], ignore_index=True)
    print("        must-have note", MUST_HAVE_NOTE_ID, "moved to the top")
    return notes
