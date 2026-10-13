# check_dataset.py
#
# Checks the dataset in dataset/helpful/ and prints PASS or FAIL for each check.
#
# How to run:
#   python check_dataset.py                    (checks dataset/helpful)
#   python check_dataset.py some/other/folder  (checks another folder)

import os
import sys

import pandas as pd


def load(folder, file_name):
    path = os.path.join(folder, file_name)
    table = pd.read_csv(path, dtype={"noteId": str, "tweetId": str}, low_memory=False)
    print("Loaded", file_name, ":", len(table), "rows")
    return table


def check(title, passed):
    # print the result of one check and give it back
    if passed:
        print("  [PASS]", title)
    else:
        print("  [FAIL]", title)
    return passed


def main():
    folder = os.path.join("dataset", "helpful")
    if len(sys.argv) > 1:
        folder = sys.argv[1]

    if not os.path.isdir(folder):
        print("Folder not found:", folder)
        print("Run build_helpful_dataset.py first to make it.")
        return

    print("Checking folder:", folder)
    print()

    notes = load(folder, "notes.csv")
    status = load(folder, "note_status.csv")
    ratings = load(folder, "ratings.csv")
    tweets = load(folder, "tweets.csv")
    combined = load(folder, "combined.csv")
    print()

    note_ids = set(notes["noteId"])
    status_ids = set(status["noteId"])
    rating_ids = set(ratings["noteId"])
    combined_ids = set(combined["noteId"])
    note_tweet_ids = set(notes["tweetId"])
    tweet_ids = set(tweets["tweetId"])

    # notes that were added by hand have no ratings yet
    manual_ids = set()
    for note_id in note_ids:
        if note_id.startswith("MANUAL-"):
            manual_ids.add(note_id)

    results = []

    print("Step 1: notes")
    results.append(check("every row in notes.csv is a different note", len(note_ids) == len(notes)))
    all_helpful = (status["currentStatus"] == "CURRENTLY_RATED_HELPFUL").all()
    results.append(check("every note is CURRENTLY_RATED_HELPFUL", all_helpful))

    print()
    print("Step 2: tweets")
    results.append(check("every note's tweet is in tweets.csv", note_tweet_ids.issubset(tweet_ids)))
    all_ok = (tweets["tweet_status"] == "ok").all()
    results.append(check("every tweet was found (status ok)", all_ok))
    has_text = combined["tweet_text"].notna().all()
    results.append(check("every note has tweet text", has_text))
    all_english = (tweets["tweet_lang"] == "en").all()
    results.append(check("every tweet is in English", all_english))

    print()
    print("Step 3: same notes in every file")
    results.append(check("note_status.csv has the same notes", status_ids == note_ids))
    results.append(check("ratings.csv has the same notes (except notes added by hand)",
                         rating_ids == note_ids - manual_ids))
    results.append(check("combined.csv has the same notes", combined_ids == note_ids))

    if len(manual_ids) > 0:
        print("  [INFO]", len(manual_ids), "note(s) added by hand, no ratings yet:", manual_ids)

    print()
    print("Extra info")
    print("  different tweets:", len(tweet_ids))
    ratings_per_note = ratings.groupby("noteId").size()
    print("  ratings per note (median):", int(ratings_per_note.median()))
    print("  languages:", tweets["tweet_lang"].value_counts().to_dict())

    print()
    if False in results:
        print("SOME CHECKS FAILED")
    else:
        print("ALL CHECKS PASSED")


main()
