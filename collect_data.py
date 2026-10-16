"""Step 3: collect the Notes, Ratings and Note Status rows of the chosen notes."""

from settings import read_rows_for_notes


def filter_datasets(chosen_ids: set):
    """Take every row of the chosen notes from the three datasets.

    Args:
        chosen_ids: the noteIds chosen in step 2.

    Returns:
        notes: one row per note.
        ratings: one row per rating, from all ratings files.
        status: one row per note.
    """
    print("Step 3: taking the rows of the chosen notes from Notes, Ratings and Note Status")

    notes = read_rows_for_notes("notes", chosen_ids)
    ratings = read_rows_for_notes("ratings", chosen_ids)
    status = read_rows_for_notes("noteStatusHistory", chosen_ids)

    return notes, ratings, status
