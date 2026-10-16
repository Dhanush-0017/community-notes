# Helpful notes dataset

Made with build_helpful_dataset.py (random seed 42).
500 random notes written between 2026-10-05 and 2026-10-13.
Every note is rated Helpful and is in Notes, Note Status and Ratings.
Every note is on a different tweet. If a tweet had more than one Helpful note,
the note with the most ratings was kept.
Every tweet is in English.

Note 2109061654621098457 (the "SAUDI IS BURNING" tweet) was added on purpose, not at random.

## Files
- tweets.csv: one row per tweet (from the X API). Key: tweetId
- notes.csv: one row per note. Keys: noteId, tweetId
- note_status.csv: one row per note. Key: noteId
- ratings.csv: one row per rating. Key: noteId
- combined.csv: one row per note with its tweet, both labels and rating counts

## How the files connect
- noteId connects notes, note_status, ratings and combined
- tweetId connects notes and tweets

## Limits
- 9 ratings files were used.
- Notes whose tweet was deleted or not in English were replaced by the next random note.
- Notes from the last days have fewer ratings, because people were still rating them when X made the download.
