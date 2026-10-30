# "SAUDI IS BURNING" tweet (2109031558967615703)

Everything X's Community Notes data has about this one tweet (download up to Oct 13, 2026), made with `find_tweet_data.py`.
1 tweet, 4 notes, 456 ratings by 263 raters. Only Note 4 was shown on X.

## Files

| File | One row is | Key columns |
|---|---|---|
| `combined.csv` | one note, with the tweet and rating counts | `note_label`, `writer_type`, `note_text`, `classification2` |
| `notes.csv` | one note | `note_label`, `writer_type`, `summary` (note text), `misleading...` reasons, `writer_...` |
| `note_status.csv` | X's decision about one note | `note_label`, `currentStatus`, `currentExpansionStatus`, `currentDecidedBy` |
| `ratings.csv` | one person's rating of one note | `note_label`, `helpfulnessLevel`, `helpful...` / `notHelpful...` reasons, `rater_...` |
| `note_requests.csv` | the note requests for the tweet | `suggestions` (request texts), `api...FeedEligibleAtMillis` (when AI writers could see it) |
| `user_enrollment.csv` | one person (rater or writer) | `enrollmentState`, `modelingPopulation`, `modelingGroup` |

## Added columns

- `note_label`: Note 1 to Note 4, in the order the notes were written.
- `writer_type`: `AI` if the writer's status is `apiEarnedIn` (an AI note writer using X's API),
  `Collaborative` for an AI-drafted collaborative note, otherwise `Human`.
- `writer_...` (in notes): the note writer's row from User Enrollment.
- `rater_...` (in ratings): the rater's row from User Enrollment, e.g. `rater_modelingGroup`.

Times ending in `Millis` are milliseconds since Jan 1, 1970 (UTC).
