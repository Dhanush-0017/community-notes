# Community Notes: 500 Helpful notes dataset

Built with build_helpful_dataset.py (random seed 42).
Tweet language: en.
Every note is rated **Helpful** and appears in Notes, Note Status and Ratings.

## Files and how they connect
| File | One row is | Key columns |
|---|---|---|
| tweets.csv | one tweet (from the X API) | tweetId |
| notes.csv | one note (all original columns) | noteId, tweetId |
| ratings.csv | one person's rating of one note | noteId |
| note_status.csv | the status of one note | noteId |
| combined.csv | one note with its tweet, labels and rating counts | noteId, tweetId |

- noteId links notes, ratings, note_status and combined
- tweetId links notes and tweets

## Main columns
- classification1: writer's label on the post (MISINFORMED_OR_POTENTIALLY_MISLEADING / NOT_MISLEADING)
- classification2: algorithm's label on the note (here always CURRENTLY_RATED_HELPFUL)
- note_text: the note written by the contributor (with source links)
- tweet_text: the post the note is about (full text, from the X API)
- ratings_*: number of Helpful / Somewhat / Not Helpful ratings

## Notes
- Ratings files used: 2 of 9, so rating counts may be partial.
- Notes whose tweet was deleted or unavailable were replaced by other random Helpful notes.

## Manually added post
- 1 extra note was added by hand: noteId MANUAL-2109031558967615703 (tweetId 2109031558967615703, "SAUDI IS BURNING", Oct 10, 2026).
- Its tweet info comes from the X API. The note text and "Helpful" status come from the note shown on X.
- X has not published this note in its data yet, so the real noteId, note details and ratings are missing.
  When new data is downloaded, replace MANUAL-... with the real noteId and add its ratings.
- This note was NOT chosen randomly.
