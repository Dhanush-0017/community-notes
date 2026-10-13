# build_helpful_dataset.py
#
# Builds a dataset of 500 Helpful Community Notes whose tweets are in English.
#
# Step 1: Find the Helpful notes that are in all 3 datasets
#         (Note Status says Helpful, the note is in Notes, and the note has Ratings).
#         Then put them in a random order.
# Step 2: Get the tweet of each note from the X API.
#         Keep a note only if its tweet still exists and is in English.
#         Stop when we have 500 notes.
# Step 3: Take the rows of those 500 notes from Notes, Ratings and Note Status.
# Extra:  Make one combined file and a README.
#
# All files are saved in dataset/helpful/
#
# How to run:
#   python build_helpful_dataset.py               (real run, uses the X API)
#   python build_helpful_dataset.py --no-tweets   (test run, does not use the X API)
#
# Every tweet we read is saved in dataset/tweet_cache.csv,
# so if we run the code again we do not pay for the same tweet twice.

import glob
import os
import sys

import pandas as pd


# Where the raw data from X is. We write the paths one by one, so the code
# never reads other folders by mistake (for example a newer download in data/dataset_10_12).
NOTES_FILES = os.path.join("data", "notes", "notes-*.tsv")
RATINGS_FILES = os.path.join("data", "ratings", "ratings-*.tsv")
STATUS_FILES = os.path.join("data", "noteStatusHistory-*.tsv")

OUTPUT_FOLDER = os.path.join("dataset", "helpful")
CACHE_FILE = os.path.join("dataset", "tweet_cache.csv")

NUMBER_OF_NOTES = 500
LANGUAGE = "en"          # keep only English tweets
RANDOM_SEED = 42         # same seed = same random order every time
BATCH_SIZE = 100         # how many notes we try at a time in Step 2
COST_PER_TWEET = 0.005   # price of reading one tweet from X (US dollars)


# ---------------- helper functions ----------------

def find_files(name_start):
    # Give back the list of files for one dataset: "notes", "ratings" or "noteStatusHistory"
    if name_start == "notes":
        pattern = NOTES_FILES
    elif name_start == "ratings":
        pattern = RATINGS_FILES
    else:
        pattern = STATUS_FILES

    files = glob.glob(pattern)
    files.sort()

    if len(files) == 0:
        raise Exception("No files found for " + pattern)

    return files


def read_rows_for_notes(name_start, note_ids, columns=None):
    # Read all files of one dataset (for example all Notes files)
    # and keep only the rows whose noteId is in note_ids.
    # The files are very big, so we read 1 million rows at a time.
    kept_parts = []

    for file in find_files(name_start):
        chunks = pd.read_csv(
            file,
            sep="\t",
            usecols=columns,
            dtype={"noteId": str, "tweetId": str},   # read IDs as text so they match in every file
            quoting=3,                                # treat quote marks in the note text as normal text
            chunksize=1000000,
            low_memory=False,
        )

        for chunk in chunks:
            rows = chunk[chunk["noteId"].isin(note_ids)]
            kept_parts.append(rows)

    result = pd.concat(kept_parts, ignore_index=True)
    return result


# ---------------- Step 1: Helpful notes in all 3 datasets ----------------

def get_helpful_note_ids():
    # Read Note Status and keep the noteIds that are Helpful
    status_file = find_files("noteStatusHistory")[0]
    status = pd.read_csv(
        status_file,
        sep="\t",
        usecols=["noteId", "currentStatus"],
        dtype={"noteId": str},
    )

    helpful_rows = status[status["currentStatus"] == "CURRENTLY_RATED_HELPFUL"]
    helpful_ids = set(helpful_rows["noteId"])

    print("Step 1:", len(helpful_ids), "Helpful notes in Note Status")
    return helpful_ids


def keep_notes_in_notes_files(helpful_ids):
    # Keep the Helpful notes that are also in the Notes files.
    # We only need the noteId and the tweetId here.
    notes = read_rows_for_notes("notes", helpful_ids, columns=["noteId", "tweetId"])
    notes = notes.drop_duplicates("noteId")

    print("       ", len(notes), "of them are in Notes")
    return notes


def keep_notes_with_ratings(notes):
    # Keep only the notes that have at least one rating in the Ratings files
    note_ids = set(notes["noteId"])
    rated_ids = set()

    for file in find_files("ratings"):
        chunks = pd.read_csv(
            file,
            sep="\t",
            usecols=["noteId"],
            dtype={"noteId": str},
            chunksize=3000000,
        )

        for chunk in chunks:
            rows = chunk[chunk["noteId"].isin(note_ids)]
            for note_id in rows["noteId"]:
                rated_ids.add(note_id)

    common = notes[notes["noteId"].isin(rated_ids)]

    print("       ", len(common), "of them also have Ratings (common in all 3 datasets)")
    return common


def shuffle_notes(notes):
    # Put the notes in a random order.
    # We sort first, so we always start from the same order,
    # and the seed makes the shuffle the same every time.
    notes = notes.sort_values("noteId")
    notes = notes.sample(frac=1, random_state=RANDOM_SEED)   # frac=1 means shuffle all rows
    notes = notes.reset_index(drop=True)
    return notes


# ---------------- Step 2: get the tweets ----------------

def load_tweet_cache():
    # Read the tweets we already got from X in earlier runs.
    # The cache is a dictionary:  { tweet id: { tweet_text: ..., ... } }
    cache = {}

    if os.path.exists(CACHE_FILE):
        table = pd.read_csv(CACHE_FILE, dtype={"tweetId": str})
        rows = table.to_dict("records")
        for row in rows:
            tweet_id = row["tweetId"]
            del row["tweetId"]
            cache[tweet_id] = row

    print("       ", len(cache), "tweets already in the cache (free)")
    return cache


def cache_to_table(cache):
    # Turn the cache dictionary into a table with a tweetId column
    table = pd.DataFrame.from_dict(cache, orient="index")
    table.index.name = "tweetId"
    table = table.reset_index()
    return table


def save_tweet_cache(cache):
    table = cache_to_table(cache)
    table.to_csv(CACHE_FILE, index=False)


def is_good_tweet(tweet):
    # A tweet is good if X found it and it is in English
    if tweet.get("tweet_status") != "ok":
        return False
    if tweet.get("tweet_lang") != LANGUAGE:
        return False
    return True


def pick_notes_with_tweets(candidates):
    # Go through the shuffled notes, 100 at a time.
    # Get their tweets (from the cache, or from X if we do not have them yet).
    # Keep a note only if its tweet is good.
    # Stop when we have NUMBER_OF_NOTES notes.
    from x_api import load_token, fetch_tweets

    token = load_token()
    cache = load_tweet_cache()

    chosen_notes = []
    new_tweets_read = 0
    batch_number = 0

    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates.iloc[start:start + BATCH_SIZE]
        batch_number = batch_number + 1

        # find the tweets in this batch that are not in the cache yet
        new_ids = []
        for tweet_id in batch["tweetId"]:
            if tweet_id not in cache and tweet_id not in new_ids:
                new_ids.append(tweet_id)

        # ask X only for those tweets, and save them right away
        if len(new_ids) > 0:
            answers = fetch_tweets(new_ids, token, print_progress=False)
            for tweet_id in answers:
                cache[tweet_id] = answers[tweet_id]
            new_tweets_read = new_tweets_read + len(new_ids)
            save_tweet_cache(cache)

        # keep the notes that have a good tweet
        kept_in_this_batch = 0
        for index, note in batch.iterrows():
            tweet = cache.get(note["tweetId"], {})
            if is_good_tweet(tweet):
                chosen_notes.append(note)
                kept_in_this_batch = kept_in_this_batch + 1

            if len(chosen_notes) == NUMBER_OF_NOTES:
                break

        print("  Batch", batch_number, ": kept", kept_in_this_batch, "of", len(batch), "notes,",
              len(new_ids), "new tweets read, total", len(chosen_notes), "of", NUMBER_OF_NOTES)

        if len(chosen_notes) == NUMBER_OF_NOTES:
            break

    chosen = pd.DataFrame(chosen_notes)

    if len(chosen) < NUMBER_OF_NOTES:
        print("  Warning: only found", len(chosen), "notes")

    cost = new_tweets_read * COST_PER_TWEET
    print("Step 2:", len(chosen), "notes with tweet text")
    print("       ", new_tweets_read, "new tweets read, about $" + str(round(cost, 2)))

    # keep only the tweets of the chosen notes
    tweets = cache_to_table(cache)
    tweets = tweets[tweets["tweetId"].isin(chosen["tweetId"])]

    return chosen, tweets


# ---------------- Step 3: filter the 3 datasets by noteId ----------------

def filter_datasets(chosen_ids):
    print("Step 3: taking the rows of the chosen notes from Notes, Ratings and Note Status")

    notes = read_rows_for_notes("notes", chosen_ids)
    ratings = read_rows_for_notes("ratings", chosen_ids)
    status = read_rows_for_notes("noteStatusHistory", chosen_ids)

    return notes, ratings, status


# ---------------- Extra: combined file ----------------

def count_ratings(ratings):
    # Count how many HELPFUL, SOMEWHAT_HELPFUL and NOT_HELPFUL ratings each note got
    counts = pd.crosstab(ratings["noteId"], ratings["helpfulnessLevel"])

    # make sure all 3 columns exist, even if one level never appears
    for level in ["HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"]:
        if level not in counts.columns:
            counts[level] = 0

    counts = counts[["HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"]]
    counts.columns = ["ratings_helpful", "ratings_somewhat", "ratings_not_helpful"]
    counts["ratings_total"] = counts["ratings_helpful"] + counts["ratings_somewhat"] + counts["ratings_not_helpful"]
    return counts


def make_combined(notes, ratings, status, tweets):
    # One row per note with the most useful columns

    # 1. note columns, with clearer names
    combined = notes[["noteId", "tweetId", "classification", "summary", "createdAtMillis"]].copy()
    combined = combined.rename(columns={
        "classification": "classification1",     # writer's label
        "summary": "note_text",
        "createdAtMillis": "note_created_at",
    })
    combined["note_created_at"] = pd.to_datetime(combined["note_created_at"], unit="ms", utc=True)

    # 2. classification2 = the algorithm's label, from Note Status
    labels = status[["noteId", "currentStatus"]]
    labels = labels.rename(columns={"currentStatus": "classification2"})
    combined = combined.merge(labels, on="noteId", how="left")

    # 3. rating counts
    counts = count_ratings(ratings)
    combined = combined.merge(counts, left_on="noteId", right_index=True, how="left")

    # 4. tweet information, with the most important columns first
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

def save_files(files):
    for file_name in files:
        table = files[file_name]
        path = os.path.join(OUTPUT_FOLDER, file_name)
        table.to_csv(path, index=False)
        print("        saved", file_name, "-", len(table), "rows")


def save_readme():
    number_of_rating_files = len(find_files("ratings"))

    lines = []
    lines.append("# Helpful notes dataset")
    lines.append("")
    lines.append("Made with build_helpful_dataset.py (random seed " + str(RANDOM_SEED) + ").")
    lines.append(str(NUMBER_OF_NOTES) + " random notes. Every note is rated Helpful and is in Notes, Note Status and Ratings.")
    lines.append("Every tweet is in English.")
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
    lines.append("- " + str(number_of_rating_files) + " of 9 ratings files were used, so rating counts may be partial.")
    lines.append("- Notes whose tweet was deleted or not in English were replaced by the next random note.")

    path = os.path.join(OUTPUT_FOLDER, "README.md")
    file = open(path, "w")
    file.write("\n".join(lines) + "\n")
    file.close()


# ---------------- main ----------------

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Step 1
    helpful_ids = get_helpful_note_ids()
    notes = keep_notes_in_notes_files(helpful_ids)
    common = keep_notes_with_ratings(notes)
    candidates = shuffle_notes(common)

    if len(candidates) < NUMBER_OF_NOTES:
        print("Not enough notes:", len(candidates), "found, but", NUMBER_OF_NOTES, "needed")
        return

    # Step 2
    if "--no-tweets" in sys.argv:
        print("Step 2: skipped (--no-tweets), taking the first", NUMBER_OF_NOTES, "random notes")
        chosen = candidates.head(NUMBER_OF_NOTES)
        tweets = None
    else:
        chosen, tweets = pick_notes_with_tweets(candidates)

    # Step 3
    chosen_ids = set(chosen["noteId"])
    notes, ratings, status = filter_datasets(chosen_ids)

    # Extra
    combined = make_combined(notes, ratings, status, tweets)

    # Save
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
