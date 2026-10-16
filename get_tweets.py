"""Step 2: get the tweets of the candidate notes from the X API.

Every tweet read from X is saved in tweet_cache.csv, so the same tweet is never paid for twice.
"""

import os

import pandas as pd

from settings import CACHE_FILE, LANGUAGE, NUMBER_OF_NOTES, BATCH_SIZE, COST_PER_TWEET
from x_api import load_token, fetch_tweets


def load_tweet_cache() -> dict:
    """Read the tweets saved in earlier runs.

    Returns:
        A dictionary like { tweet id: { "tweet_text": ..., "tweet_lang": ..., ... } }.
    """
    cache = {}

    if os.path.exists(CACHE_FILE):
        # As numbers, long IDs lose their last digits, so they are read as text.
        table = pd.read_csv(CACHE_FILE, dtype={"tweetId": str, "tweet_author_id": str})

        for index, row in table.iterrows():
            tweet_id = row["tweetId"]

            tweet_info = {}
            for column in table.columns:
                if column != "tweetId":
                    tweet_info[column] = row[column]

            cache[tweet_id] = tweet_info

    print("       ", len(cache), "tweets already in the cache (free)")
    return cache


def cache_to_table(cache: dict) -> pd.DataFrame:
    """Turn the cache dictionary into a table with one row per tweet.

    Args:
        cache: the dictionary from load_tweet_cache.

    Returns:
        A table with a tweetId column followed by the tweet information.
    """
    rows = []

    for tweet_id in cache:
        row = {}
        row["tweetId"] = tweet_id

        tweet_info = cache[tweet_id]
        for column in tweet_info:
            row[column] = tweet_info[column]

        rows.append(row)

    table = pd.DataFrame(rows)
    return table


def save_tweet_cache(cache: dict):
    """Save the whole cache to tweet_cache.csv."""
    table = cache_to_table(cache)
    table.to_csv(CACHE_FILE, index=False)


def is_good_tweet(tweet: dict) -> bool:
    """Check that X found the tweet and that it is in LANGUAGE."""
    if tweet.get("tweet_status") != "ok":
        return False
    if tweet.get("tweet_lang") != LANGUAGE:
        return False
    return True


def pick_notes_with_tweets(candidates: pd.DataFrame):
    """Go through the candidates in order and keep the notes whose tweet is good.

    Tweets are taken from the cache, and only the missing ones are read from X.
    Stops when NUMBER_OF_NOTES notes are kept.

    Args:
        candidates: the notes from step 1, in the order they should be tried.

    Returns:
        chosen: the kept notes.
        tweets: a table with the tweet of each kept note.
    """
    token = load_token()
    cache = load_tweet_cache()

    chosen_notes = []
    new_tweets_read = 0
    batch_number = 0

    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates.iloc[start:start + BATCH_SIZE]
        batch_number = batch_number + 1

        new_ids = []
        for tweet_id in batch["tweetId"]:
            if tweet_id not in cache and tweet_id not in new_ids:
                new_ids.append(tweet_id)

        if len(new_ids) > 0:
            answers = fetch_tweets(new_ids, token, print_progress=False)
            for tweet_id in answers:
                cache[tweet_id] = answers[tweet_id]
            new_tweets_read = new_tweets_read + len(new_ids)

            # Save after every batch, so paid tweets are not lost if the run stops.
            save_tweet_cache(cache)

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

    all_tweets = cache_to_table(cache)
    is_chosen_tweet = all_tweets["tweetId"].isin(chosen["tweetId"])
    tweets = all_tweets[is_chosen_tweet]

    return chosen, tweets
