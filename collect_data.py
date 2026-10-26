"""Step 3: collect the Notes, Ratings and Note Status rows of the chosen notes."""

import pandas as pd

from settings import ENROLLMENT_FILE, read_rows_for_notes


def filter_datasets(chosen_ids: set):
    """Take every row of the chosen notes from the three datasets.

    Args:
        chosen_ids: the noteIds chosen in step 2.

    Returns:
        notes: one row per note, with the writer's User Enrollment fields added.
        ratings: one row per rating, from all ratings files.
        status: one row per note.
    """
    print("Step 3: taking the rows of the chosen notes from Notes, Ratings and Note Status")

    notes = read_rows_for_notes("notes", chosen_ids)
    ratings = read_rows_for_notes("ratings", chosen_ids)
    status = read_rows_for_notes("noteStatusHistory", chosen_ids)

    notes = add_writer_enrollment(notes)

    return notes, ratings, status


def add_writer_enrollment(notes: pd.DataFrame) -> pd.DataFrame:
    """Add the note writer's row from the User Enrollment file to each note.

    The new columns get the prefix "writer_", e.g. writer_enrollmentState.
    writer_enrollmentState = "apiEarnedIn" means the note was written by an AI note writer (X's API).

    Args:
        notes: one row per note, with a noteAuthorParticipantId column.

    Returns:
        The same notes with the writer_ columns added at the end.
    """
    enrollment = pd.read_csv(ENROLLMENT_FILE, sep="\t", dtype=str)

    writer_columns = {}
    for column in enrollment.columns:
        writer_columns[column] = "writer_" + column
    enrollment = enrollment.rename(columns=writer_columns)

    notes = notes.merge(
        enrollment,
        left_on="noteAuthorParticipantId",
        right_on="writer_participantId",
        how="left",
    )
    notes = notes.drop(columns=["writer_participantId"])

    return notes
