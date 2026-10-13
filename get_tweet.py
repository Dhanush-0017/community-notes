# get_tweet.py
# Get ONE tweet from the X API and print its information.
# Reading one tweet costs $0.005.
#
# How to run:
#   python get_tweet.py                                                   (test tweet)
#   python get_tweet.py 2109031558967615703                               (a tweet ID)
#   python get_tweet.py "https://x.com/MarioNawfal/status/2109031558967615703"   (a full link)

import sys

from x_api import load_token, fetch_tweets


TEST_TWEET_ID = "1146442848914608128"


def get_tweet_id():
    # if nothing is given, use the test tweet
    if len(sys.argv) < 2:
        return TEST_TWEET_ID

    text = sys.argv[1]

    # a link can end with things like ?s=20, so we remove them
    text = text.split("?")[0]
    text = text.rstrip("/")

    # the tweet ID is the last part of the link
    parts = text.split("/")
    tweet_id = parts[-1]
    return tweet_id


def main():
    tweet_id = get_tweet_id()
    token = load_token()

    tweets = fetch_tweets([tweet_id], token)

    if tweet_id not in tweets:
        print("No answer from X for this tweet")
        return

    tweet = tweets[tweet_id]

    print()
    for name in tweet:
        print(name, ":", tweet[name])


main()
