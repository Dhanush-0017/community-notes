# find_tweet_data.py
#
# Finds everything the Community Notes datasets have about ONE tweet.
#
#   1. Notes           -> notes written on this tweet          (search by tweetId)
#   2. Note Status     -> the status of those notes            (search by noteId)
#   3. Ratings         -> every rating of those notes          (search by noteId)
#   4. Note Requests   -> requests for a note on this tweet    (search by tweetId)
#   5. User Enrollment -> the people who wrote or rated them   (search by participantId)
#
# How to run:
#   python find_tweet_data.py 2109031558967615703
#   python find_tweet_data.py 2109031558967615703 --no-ratings                 (skip the big Ratings files)
#   python find_tweet_data.py 2109031558967615703 --data data/dataset_10_12    (use another data folder)
#
# The results are saved in dataset/tweet_<tweetId>/

import glob
import os
import sys

import pandas as pd


# read all ID columns as text, so they match in every file
ID_COLUMNS = {
    "noteId": str,
    "tweetId": str,
    "participantId": str,
    "noteAuthorParticipantId": str,
    "raterParticipantId": str,
}


def get_tweet_id():
    if len(sys.argv) < 2:
        print("Please give a tweet ID, for example:")
        print("  python find_tweet_data.py 2109031558967615703")
        sys.exit()

    # a full link also works: the tweet ID is the last part of the link
    text = sys.argv[1]
    text = text.split("?")[0]
    text = text.rstrip("/")
    parts = text.split("/")
    return parts[-1]


def get_data_folder():
    # use the folder after --data if it is given, otherwise the data folder
    if "--data" in sys.argv:
        position = sys.argv.index("--data")
        return sys.argv[position + 1]
    return "data"


def find_files(data_folder, names):
    # Find the files of one dataset.
    # names is a list because X has used two names for some files,
    # for example "note_request" and "batSignals" are the same dataset.
    files = []
    for name in names:
        pattern = os.path.join(data_folder, "**", name + "*.tsv")
        found = glob.glob(pattern, recursive=True)
        for file in found:
            files.append(file)
    files.sort()
    return files


def read_matching_rows(files, column, values):
    # Read the files 2 million rows at a time
    # and keep only the rows where column is one of the values.
    kept_parts = []

    for file in files:
        print("        reading", file)
        chunks = pd.read_csv(
            file,
            sep="\t",
            dtype=ID_COLUMNS,
            quoting=3,
            chunksize=2000000,
            low_memory=False,
        )
        for chunk in chunks:
            rows = chunk[chunk[column].isin(values)]
            kept_parts.append(rows)

    if len(kept_parts) == 0:
        return pd.DataFrame()

    return pd.concat(kept_parts, ignore_index=True)


def remove_repeats(table, key_columns):
    # If the data folder has two downloads of the same file (old and new),
    # the same row is found twice. Keep each row only once.
    if len(table) == 0:
        return table
    return table.drop_duplicates(key_columns)


def main():
    tweet_id = get_tweet_id()
    data_folder = get_data_folder()

    print("Looking for tweet", tweet_id, "in", data_folder)
    print()

    # 1. Notes written on this tweet
    print("1. Notes")
    notes_files = find_files(data_folder, ["notes"])
    notes = read_matching_rows(notes_files, "tweetId", [tweet_id])
    notes = remove_repeats(notes, ["noteId"])
    print("   ->", len(notes), "notes found")
    print()

    note_ids = []
    if len(notes) > 0:
        note_ids = list(notes["noteId"])

    # 2. Status of those notes
    print("2. Note Status")
    status_files = find_files(data_folder, ["noteStatusHistory"])
    status = read_matching_rows(status_files, "noteId", note_ids)
    status = remove_repeats(status, ["noteId"])
    print("   ->", len(status), "status rows found")
    print()

    # 3. Ratings of those notes
    if "--no-ratings" in sys.argv:
        print("3. Ratings: skipped (--no-ratings)")
        ratings = pd.DataFrame()
    else:
        print("3. Ratings (big files, this takes a few minutes)")
        ratings_files = find_files(data_folder, ["ratings"])
        ratings = read_matching_rows(ratings_files, "noteId", note_ids)
        ratings = remove_repeats(ratings, ["noteId", "raterParticipantId"])
        print("   ->", len(ratings), "ratings found")
    print()

    # 4. Requests for a note on this tweet
    print("4. Note Requests")
    request_files = find_files(data_folder, ["note_request", "batSignals"])
    note_requests = read_matching_rows(request_files, "tweetId", [tweet_id])
    note_requests = remove_repeats(note_requests, ["tweetId"])
    print("   ->", len(note_requests), "request rows found")
    print()

    # 5. The people who wrote or rated the notes
    print("5. User Enrollment")
    people = []
    if len(notes) > 0:
        for person in notes["noteAuthorParticipantId"]:
            people.append(person)
    if len(ratings) > 0:
        for person in ratings["raterParticipantId"]:
            people.append(person)

    user_files = find_files(data_folder, ["user_enrollment", "userEnrollment"])
    users = read_matching_rows(user_files, "participantId", people)
    users = remove_repeats(users, ["participantId"])
    print("   ->", len(users), "users found")
    print()

    # save every result in its own file
    output_folder = os.path.join("dataset", "tweet_" + tweet_id)
    os.makedirs(output_folder, exist_ok=True)

    notes.to_csv(os.path.join(output_folder, "notes.csv"), index=False)
    status.to_csv(os.path.join(output_folder, "note_status.csv"), index=False)
    ratings.to_csv(os.path.join(output_folder, "ratings.csv"), index=False)
    note_requests.to_csv(os.path.join(output_folder, "note_requests.csv"), index=False)
    users.to_csv(os.path.join(output_folder, "user_enrollment.csv"), index=False)

    print("Summary")
    print("   notes.csv:          ", len(notes), "rows")
    print("   note_status.csv:    ", len(status), "rows")
    print("   ratings.csv:        ", len(ratings), "rows")
    print("   note_requests.csv:  ", len(note_requests), "rows")
    print("   user_enrollment.csv:", len(users), "rows")
    print()

    if len(notes) > 0:
        print("Notes on this tweet:")
        for index, note in notes.iterrows():
            print("  ", note["noteId"], ":", str(note["summary"])[:100])
    else:
        print("No notes found. If the tweet is new, download newer data from X and run this again.")

    print()
    print("Saved in", output_folder)


main()
