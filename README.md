# X Community Notes: how a note gets shown

This project uses X's public Community Notes data to understand how X decides which note is shown under a tweet.

Community Notes in short: people write notes on tweets, other people rate the notes (Helpful / Somewhat / Not Helpful), and X's algorithm decides which note is shown.

## Overview

1. **Dataset:** 500 recent Helpful notes on 500 English tweets (Oct 5-12, 2026) -> `dataset/10-05_10-13/`
2. **EDA:** `eda_summary.ipynb`. Main finding: 63% of the Helpful notes were written by AI note writers.
3. **Case study:** one tweet ("SAUDI IS BURNING") with 4 notes, where only Note 4 was shown -> `dataset/tweet_2109031558967615703/`
4. **X's steps on that tweet**, based on X's open-source code (github.com/twitter/communitynotes) -> `saudi_summary.ipynb` and `score_with_x_model.py`:
   - which raters X trusts (trust score from their past ratings)
   - which model decides (Core or Expansion)
   - each note's helpfulness score and one-sidedness, using X's own model code

**Result:** Note 4 was not shown because it got more votes. It was shown because raters who usually disagree **both** found it helpful. Notes 1-3 were liked mostly by one side.

## How it works

```
raters -> trusted or not -> they rate the 4 notes -> X's model -> score + one-sidedness -> shown / waiting / blocked
```

- **Trusted rater:** of their past ratings made before X decided, at least 66% matched X's final decision, and they have 10+ ratings.
- **Which model:** a model only decides a note if half of its ratings come from that model's rater groups. Here only 19-25% came from Core groups, so the Expansion model decided.
- **Shown:** helpfulness score 0.40+ and one-sidedness under 0.5.

## How the files connect

| Key | Connects |
|---|---|
| `noteId` | notes, ratings and note status |
| `raterParticipantId` / `noteAuthorParticipantId` | a rating or a note to the person in User Enrollment (`participantId`) |
| `tweetId` | a note to its tweet |

## The data

The raw data comes from X: https://communitynotes.x.com/guide/en/under-the-hood/download-data

It is about 45 GB, so it is not in this repository. Download it and put it in a `data` folder:

```
data/
├── notes/notes-00000.tsv ... notes-00004.tsv
├── ratings/ratings-00000.tsv ... ratings-00008.tsv
├── noteStatusHistory-00000.tsv
├── batSignals-00000.tsv          (note requests)
└── userEnrollment-00000.tsv
```

Data version used: the download with data up to Oct 13, 2026.

### Saudi tweet folder (`dataset/tweet_2109031558967615703/`)

| File | One row is | Important columns |
|---|---|---|
| `notes.csv` | one note | `note_label`, `summary` (note text), `writer_type`, `writer_enrollmentState` (`apiEarnedIn` = AI) |
| `ratings.csv` | one rating | `raterParticipantId`, `helpfulnessLevel`, `rater_modelingPopulation`, `rater_modelingGroup` |
| `note_status.csv` | X's decision on one note | `currentStatus`, `currentExpansionStatus`, `currentDecidedBy` |
| `user_enrollment.csv` | one person | `enrollmentState`, `modelingPopulation`, `modelingGroup` |
| `note_requests.csv` | a request for a note | `suggestions` |
| `combined.csv` | one note with its tweet | `tweet_text`, `note_text` |
| `rater_profiles.csv` | one rater (made in `saudi_summary.ipynb`) | `valid_ratings`, `agreeing_ratings`, `trust_score`, `trusted` |
| `model_scores.csv` | one note (made by `score_with_x_model.py`) | `helpfulness_score`, `one_sidedness` |
| `rater_sides.csv` | one rater (made by `score_with_x_model.py`) | `rater_side`, `rater_generosity` |

### 500-note folder (`dataset/10-05_10-13/`)

`notes.csv`, `ratings.csv`, `note_status.csv`, `tweets.csv`, `combined.csv` (one row = one note with its tweet and rating counts), and the same files in `10-05_10-13.xlsx`.

How the notes were chosen: Helpful notes written Oct 5-13, 2026, one note per tweet (the one with the most ratings), random order (seed 42), English tweets that still exist, stop at 500. The Saudi note is always included.

## Files

| File | What it does |
|---|---|
| `build_helpful_dataset.py` | builds the 500-note dataset (uses `choose_notes.py`, `get_tweets.py`, `collect_data.py`) |
| `settings.py` | dates, paths and other settings |
| `x_api.py`, `get_tweet.py` | read tweets from the X API |
| `find_tweet_data.py` | collects everything about one tweet into `dataset/tweet_<tweetId>/` |
| `check_dataset.py` | checks a dataset folder (PASS / FAIL) |
| `eda_10-05_10-13.ipynb` | full EDA of the 500 notes |
| `eda_summary.ipynb` | the 4 main EDA findings |
| `saudi_summary.ipynb` | the Saudi tweet, step by step |
| `saudi_tweet.ipynb` | an older, shorter look at the Saudi tweet |
| `score_with_x_model.py` | runs X's own model on one month of ratings |
| `Community_Notes_Overview.drawio` | diagram of the flow |

## How to run

Python 3.10+, then `pip install -r requirements.txt`. For the X API, make a `.env` file with `X_API=your_bearer_token`.

```
python build_helpful_dataset.py                  # build the 500-note dataset (uses the X API)
python check_dataset.py dataset/10-05_10-13      # check it
python find_tweet_data.py 2109031558967615703    # everything about one tweet
```

To run `score_with_x_model.py`, put X's code next to this folder (`../communitynotes`), install `torch pyarrow wandb`, and run `WANDB_MODE=disabled python score_with_x_model.py`.

## Limits

- The model scores use one month of ratings; X uses its full history, so these scores are lower than X's. Compare the notes with each other.
- The trust score is a close copy of X's rule. It skips the small penalty for rating abusive notes as Helpful.
- Notes from the last days of the date range have fewer ratings, because people were still rating them.
- Deleted or private tweets were skipped.
