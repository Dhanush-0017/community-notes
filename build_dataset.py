# build_dataset.py
#
# Builds a small random sample of 200 Community Notes (any status),
# with the tweet text and both labels.
#
#   label1_writer    = what the note writer said about the tweet (Misleading / Not misleading)
#   label2_algorithm = what the algorithm decided about the note (Helpful / Not Helpful / ...)
#
# Step 1: pick 200 random notes from the Notes files
# Step 2: add the status of each note (Note Status file)
# Step 3: count the ratings of each note (Ratings files)
# Step 4: get the tweet text from the X API (tweets in dataset/tweet_cache.csv are free)
# Step 5: save the dataset
#
# Output:
#   dataset/community_notes_sample_200.csv        (13 clean columns)
#   dataset/community_notes_sample_200_full.csv   (all columns)
#
# How to run:
#   python build_dataset.py               (real run, uses the X API)
#   python build_dataset.py --no-tweets   (test run, does not use the X API)

import glob
import html
import os
import sys

import pandas as pd


NOTES_FILES = os.path.join("data", "notes", "notes-*.tsv")
RATINGS_FILES = os.path.join("data", "ratings", "ratings-*.tsv")
STATUS_FILES = os.path.join("data", "noteStatusHistory-*.tsv")

OUTPUT_FOLDER = "dataset"
CACHE_FILE = os.path.join("dataset", "tweet_cache.csv")

SAMPLE_SIZE = 200
RANDOM_SEED = 42
COST_PER_TWEET = 0.005

# simple names for the labels
WRITER_LABELS = {
    "MISINFORMED_OR_POTENTIALLY_MISLEADING": "Misleading",
    "NOT_MISLEADING": "Not misleading",
}
ALGORITHM_LABELS = {
    "CURRENTLY_RATED_HELPFUL": "Helpful",
    "CURRENTLY_RATED_NOT_HELPFUL": "Not Helpful",
    "NEEDS_MORE_RATINGS": "Needs More Ratings",
}


# ---------------- helper functions ----------------

def get_files(pattern):
    files = glob.glob(pattern)
    files.sort()
    if len(files) == 0:
        raise Exception("No files found for " + pattern)
    return files


def clean_text(text):
    # Note text sometimes has things like &amp;amp; instead of &.
    # html.unescape fixes this. We do it twice because some text is changed twice.
    if not isinstance(text, str):
        return text
    text = html.unescape(text)
    text = html.unescape(text)
    return text


def millis_to_date(column):
    # The data saves time as milliseconds since 1970.
    # Some values are wrong or empty, so we turn only the good ones into dates.
    numbers = pd.to_numeric(column, errors="coerce")
    good = (numbers >= 0) & (numbers <= 4102444800000)    # before the year 2100
    numbers = numbers.where(good)
    return pd.to_datetime(numbers, unit="ms", utc=True)


# ---------------- Step 1: random notes ----------------

def pick_random_notes():
    # first read only the noteIds, so we do not load all the text into memory
    id_tables = []
    for file in get_files(NOTES_FILES):
        table = pd.read_csv(file, sep="\t", usecols=["noteId"], dtype={"noteId": str}, quoting=3)
        id_tables.append(table)

    all_ids = pd.concat(id_tables, ignore_index=True)
    all_ids = all_ids.drop_duplicates("noteId")
    all_ids = all_ids.sort_values("noteId")              # same starting order every time
    picked = all_ids.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED)
    picked_ids = set(picked["noteId"])

    # now read the full rows, but only for the picked notes
    kept_parts = []
    for file in get_files(NOTES_FILES):
        chunks = pd.read_csv(
            file,
            sep="\t",
            dtype={"noteId": str, "tweetId": str},
            quoting=3,
            chunksize=1000000,
            low_memory=False,
        )
        for chunk in chunks:
            rows = chunk[chunk["noteId"].isin(picked_ids)]
            kept_parts.append(rows)

    sample = pd.concat(kept_parts, ignore_index=True)
    sample = sample.drop_duplicates("noteId")
    sample = sample.reset_index(drop=True)

    print("Step 1: picked", len(sample), "random notes out of", len(all_ids))
    return sample


# ---------------- Step 2: note status ----------------

def add_status(sample):
    status_file = get_files(STATUS_FILES)[0]
    status = pd.read_csv(status_file, sep="\t", usecols=["noteId", "currentStatus"], dtype={"noteId": str})

    sample = sample.merge(status, on="noteId", how="left")

    # notes that are not in Note Status were never scored
    sample["currentStatus"] = sample["currentStatus"].fillna("Not scored")

    print("Step 2: added the note status")
    return sample


# ---------------- Step 3: rating counts ----------------

def add_rating_counts(sample):
    note_ids = set(sample["noteId"])
    kept_parts = []

    for file in get_files(RATINGS_FILES):
        chunks = pd.read_csv(
            file,
            sep="\t",
            usecols=["noteId", "helpfulnessLevel"],
            dtype={"noteId": str},
            chunksize=3000000,
        )
        for chunk in chunks:
            rows = chunk[chunk["noteId"].isin(note_ids)]
            kept_parts.append(rows)

    ratings = pd.concat(kept_parts, ignore_index=True)

    # count each type of rating for each note
    counts = pd.crosstab(ratings["noteId"], ratings["helpfulnessLevel"])
    for level in ["HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"]:
        if level not in counts.columns:
            counts[level] = 0
    counts = counts[["HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"]]
    counts.columns = ["ratings_helpful", "ratings_somewhat", "ratings_not_helpful"]

    sample = sample.merge(counts, left_on="noteId", right_index=True, how="left")

    # notes with no ratings get 0
    for column in ["ratings_helpful", "ratings_somewhat", "ratings_not_helpful"]:
        sample[column] = sample[column].fillna(0)
        sample[column] = sample[column].astype(int)

    print("Step 3: counted", len(ratings), "ratings")
    return sample


# ---------------- Step 4: tweets ----------------

def load_tweet_cache():
    cache = {}
    if os.path.exists(CACHE_FILE):
        table = pd.read_csv(CACHE_FILE, dtype={"tweetId": str})
        rows = table.to_dict("records")
        for row in rows:
            tweet_id = row["tweetId"]
            del row["tweetId"]
            cache[tweet_id] = row
    return cache


def cache_to_table(cache):
    table = pd.DataFrame.from_dict(cache, orient="index")
    table.index.name = "tweetId"
    table = table.reset_index()
    return table


def add_tweets(sample):
    from x_api import load_token, fetch_tweets

    cache = load_tweet_cache()

    # only ask X for tweets that are not in the cache
    new_ids = []
    for tweet_id in sample["tweetId"]:
        if tweet_id not in cache and tweet_id not in new_ids:
            new_ids.append(tweet_id)

    if len(new_ids) > 0:
        token = load_token()
        answers = fetch_tweets(new_ids, token)
        for tweet_id in answers:
            cache[tweet_id] = answers[tweet_id]
        cache_to_table(cache).to_csv(CACHE_FILE, index=False)

    tweets = cache_to_table(cache)
    tweets = tweets[tweets["tweetId"].isin(sample["tweetId"])]
    sample = sample.merge(tweets, on="tweetId", how="left")

    found = 0
    for status in sample["tweet_status"]:
        if status == "ok":
            found = found + 1

    cost = len(new_ids) * COST_PER_TWEET
    print("Step 4:", found, "of", len(sample), "tweets found")
    print("       ", len(new_ids), "new tweets read, about $" + str(round(cost, 2)))
    return sample


# ---------------- Step 5: clean table and save ----------------

def get_column(table, name):
    # give back the column if it exists, otherwise an empty column
    # (the tweet columns do not exist in a --no-tweets run)
    if name in table.columns:
        return table[name]
    return None


def make_clean_table(sample):
    clean = pd.DataFrame()
    clean["noteId"] = sample["noteId"]
    clean["tweetId"] = sample["tweetId"]
    clean["tweet_text"] = get_column(sample, "tweet_text")
    clean["note_text"] = sample["summary"].apply(clean_text)
    clean["label1_writer"] = sample["classification"].map(WRITER_LABELS)
    clean["label2_algorithm"] = sample["currentStatus"].map(ALGORITHM_LABELS).fillna("Not scored")
    clean["note_created_at"] = millis_to_date(sample["createdAtMillis"])
    clean["tweet_created_at"] = get_column(sample, "tweet_created_at")
    clean["tweet_lang"] = get_column(sample, "tweet_lang")
    clean["tweet_like_count"] = get_column(sample, "tweet_like_count")
    clean["tweet_retweet_count"] = get_column(sample, "tweet_retweet_count")
    clean["ratings_helpful"] = sample["ratings_helpful"]
    clean["ratings_not_helpful"] = sample["ratings_not_helpful"]
    return clean


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    sample = pick_random_notes()
    sample = add_status(sample)
    sample = add_rating_counts(sample)

    if "--no-tweets" in sys.argv:
        print("Step 4: skipped (--no-tweets)")
    else:
        sample = add_tweets(sample)

    clean = make_clean_table(sample)

    clean_path = os.path.join(OUTPUT_FOLDER, "community_notes_sample_" + str(SAMPLE_SIZE) + ".csv")
    full_path = os.path.join(OUTPUT_FOLDER, "community_notes_sample_" + str(SAMPLE_SIZE) + "_full.csv")

    clean.to_csv(clean_path, index=False)
    sample.to_csv(full_path, index=False)

    print("Step 5: saved", clean_path, "(" + str(len(clean.columns)) + " columns)")
    print("        saved", full_path, "(" + str(len(sample.columns)) + " columns)")


main()
