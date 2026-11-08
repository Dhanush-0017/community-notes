# Paired dataset: Helpful and Not Helpful notes on the same tweets

Made with build_paired_dataset.py (random seed 42).
500 English tweets. Each has a Helpful note written between 2026-05-01 and 2026-10-13 and at least one Not Helpful note.

## Files (each as .csv and .xlsx, one row per note)
- helpful: 500 notes, one per tweet (CURRENTLY_RATED_HELPFUL, the one with the most ratings)
- not_helpful: 614 notes, every CURRENTLY_RATED_NOT_HELPFUL note on those tweets
- balanced: 1000 notes, one Helpful and one Not Helpful per tweet (500 + 500).
  If a tweet has more than one Not Helpful note, the one with the most ratings is kept.
  Column label (helpful / not_helpful) is the true answer for testing a model.

## Main columns
- tweetId: connects the two files (same tweet)
- tweet_text, note_text
- classification1: the writer's label (misleading or not)
- classification2: X's status (currentStatus)
- writer_enrollmentState: apiEarnedIn means an AI note writer
- ratings_helpful, ratings_somewhat, ratings_not_helpful, ratings_total
- tweet_ columns: from the X API (likes, retweets, replies, ...)

## Limits
- Only about 4 tweets a day get both kinds of notes, so the dates start on 2026-05-01.
- Tweets that were deleted or not in English were skipped.
