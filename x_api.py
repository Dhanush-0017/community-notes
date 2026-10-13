# x_api.py
# Functions to get tweets from the X API.
# The other scripts use these functions.

import time
import requests


API_URL = "https://api.x.com/2/tweets"

# Extra information we ask X to send for each tweet.
# note_tweet gives us the full text of long tweets (more than 280 characters).
TWEET_FIELDS = "created_at,author_id,lang,public_metrics,note_tweet"

# X allows at most 100 tweet IDs in one request
MAX_IDS_PER_REQUEST = 100


def load_token():
    # Read the X API key from the .env file.
    # The line in .env looks like:  X_API=your_key_here
    file = open(".env")
    lines = file.readlines()
    file.close()

    for line in lines:
        if "=" not in line:
            continue

        # split only at the first "=" because the key itself can contain "="
        parts = line.split("=", 1)
        name = parts[0].strip()
        value = parts[1].strip()
        value = value.strip('"')

        if name == "X_API":
            return value

    raise Exception("Could not find X_API in the .env file")


def request_tweets(tweet_ids, token):
    # Send ONE request to X for up to 100 tweet IDs.
    # Returns the answer from X (a dictionary).
    headers = {"Authorization": "Bearer " + token}
    params = {
        "ids": ",".join(tweet_ids),
        "tweet.fields": TWEET_FIELDS,
    }

    while True:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)

        # 429 means "too many requests", so we wait one minute and try again
        if response.status_code == 429:
            print("  Rate limit reached, waiting 60 seconds...")
            time.sleep(60)
            continue

        # any other error (wrong key, no credits, ...) -> stop and show the error
        if response.status_code != 200:
            raise Exception("X API error " + str(response.status_code) + ": " + response.text[:300])

        return response.json()


def read_one_tweet(tweet):
    # Take one tweet from X's answer and keep only the parts we need.

    # long tweets have their full text inside "note_tweet"
    if "note_tweet" in tweet:
        text = tweet["note_tweet"]["text"]
    else:
        text = tweet["text"]

    metrics = {}
    if "public_metrics" in tweet:
        metrics = tweet["public_metrics"]

    row = {}
    row["tweet_status"] = "ok"
    row["tweet_text"] = text
    row["tweet_created_at"] = tweet.get("created_at")
    row["tweet_author_id"] = tweet.get("author_id")
    row["tweet_lang"] = tweet.get("lang")
    row["tweet_like_count"] = metrics.get("like_count")
    row["tweet_retweet_count"] = metrics.get("retweet_count")
    row["tweet_reply_count"] = metrics.get("reply_count")
    row["tweet_quote_count"] = metrics.get("quote_count")
    return row


def fetch_tweets(tweet_ids, token, print_progress=True):
    # Get many tweets, 100 at a time.
    # Returns a dictionary like this:
    #   { "tweet id": { "tweet_text": ..., "tweet_like_count": ..., ... } }
    # If a tweet is deleted or private, it gets a tweet_status that says why.

    # make sure every ID is text
    ids = []
    for tweet_id in tweet_ids:
        ids.append(str(tweet_id))

    results = {}
    batch_number = 0

    for start in range(0, len(ids), MAX_IDS_PER_REQUEST):
        batch = ids[start:start + MAX_IDS_PER_REQUEST]
        batch_number = batch_number + 1

        answer = request_tweets(batch, token)

        # tweets that X found
        found_tweets = answer.get("data", [])
        for tweet in found_tweets:
            results[tweet["id"]] = read_one_tweet(tweet)

        # tweets that X could not give us (deleted, private, suspended account ...)
        errors = answer.get("errors", [])
        for error in errors:
            missing_id = error.get("value")
            if missing_id is None:
                missing_id = error.get("resource_id")

            if missing_id is not None and missing_id not in results:
                reason = error.get("title", "unavailable")
                results[missing_id] = {"tweet_status": reason}

        if print_progress:
            print("  Batch", batch_number, ":", len(found_tweets), "of", len(batch), "tweets found")

    return results
