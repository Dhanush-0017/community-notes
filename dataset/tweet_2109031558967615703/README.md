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
| `rater_profiles.csv` | one rater (made in `saudi_summary.ipynb`, section 8) | `trust_score`, `trusted`, `total_ratings`, `valid_ratings`, `first_rating` |
| `model_scores.csv` | one note, scored by X's own model (made by `score_with_x_model.py`) | `helpfulness_score`, `one_sidedness` |
| `rater_sides.csv` | one rater, from X's own model (made by `score_with_x_model.py`) | `rater_side`, `rater_generosity` |

## Added columns

- `note_label`: Note 1 to Note 4, in the order the notes were written.
- `writer_type`: `AI` if the writer's status is `apiEarnedIn` (an AI note writer using X's API),
  `Collaborative` for an AI-drafted collaborative note, otherwise `Human`.
- `writer_...` (in notes): the note writer's row from User Enrollment.
- `rater_...` (in ratings): the rater's row from User Enrollment, e.g. `rater_modelingGroup`.

Times ending in `Millis` are milliseconds since Jan 1, 1970 (UTC).
