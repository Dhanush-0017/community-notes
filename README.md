# X Community Notes Dataset

This project works with data from X Community Notes. Community Notes is X's system where users add notes to posts that may be misleading. Other users rate the notes, and an algorithm decides if a note is shown under the post.

X shares all notes, ratings and note statuses as public data. This project uses that data together with the X API to build a clean dataset for research.

This is part of my work as a Graduate Research Assistant at Georgia State University.

## What this project does

1. Builds a dataset of **500 recent Helpful notes on 500 different English tweets** (`dataset/recent_helpful/`).
2. Finds **all data about one tweet** across the Community Notes datasets.
3. Checks that a dataset is correct.

## The data

The raw data comes from X: https://communitynotes.x.com/guide/en/under-the-hood/download-data

It is not in this repository because it is too big (about 45 GB). To run the code, download it and put it in a `data` folder like this:

```
data/
├── notes/notes-00000.tsv ... notes-00004.tsv
├── ratings/ratings-00000.tsv ... ratings-00008.tsv
├── noteStatusHistory-00000.tsv
├── batSignals-00000.tsv          (note requests)
└── userEnrollment-00000.tsv
```

The current dataset uses the download with data up to **Oct 13, 2026**.

The datasets are connected by IDs:

- `noteId` connects Notes, Note Status and Ratings
- `tweetId` connects a note to its tweet
- `participantId` connects a person to User Enrollment

One tweet can have many notes, and one note can have many ratings. A note is shown on X only when it is rated **Helpful**.

Each note has two labels:

- **classification1**: the writer's label on the tweet (misleading or not misleading)
- **classification2**: the algorithm's label on the note (Helpful, Not Helpful, or Needs More Ratings)

## Files

| File | What it does |
|---|---|
| `build_helpful_dataset.py` | Main file. Runs the 3 steps below and saves the dataset |
| `settings.py` | All settings (dates, paths, number of notes ...) and helpers to read the data files |
| `choose_notes.py` | Step 1: choose the candidate notes |
| `get_tweets.py` | Step 2: get the tweets from the X API |
| `collect_data.py` | Step 3: collect the Notes, Ratings and Note Status rows of the chosen notes |
| `x_api.py` | Functions to get tweets from the X API |
| `find_tweet_data.py` | Finds all data about one tweet and saves it in `dataset/tweet_<tweetId>/` |
| `check_dataset.py` | Checks a dataset folder and prints PASS or FAIL |
| `get_tweet.py` | Gets one tweet from the X API (useful to test the API key) |
| `dataset/tweet_cache.csv` | Every tweet already read from the X API, so we do not pay twice |

## The recent Helpful notes dataset (`dataset/recent_helpful/`)

| File | One row is |
|---|---|
| `notes.csv` | one note |
| `note_status.csv` | the status of one note |
| `ratings.csv` | one person's rating of one note |
| `tweets.csv` | one tweet (from the X API) |
| `combined.csv` | one note with its tweet, both labels and rating counts |

How it is made:

1. Find the notes that are Helpful in Note Status, were written between **Oct 5 and Oct 13, 2026**, are in Notes, and have Ratings.
2. If a tweet has more than one Helpful note, keep the note with the **most ratings**.
3. Put the notes in a random order (seed 42, so the result is the same every time). The note `2109061654621098457` (the "SAUDI IS BURNING" tweet) is always put first, because it was asked for.
4. Get each note's tweet from the X API. Keep the note only if the tweet still exists and is in English. Stop at 500 notes.
5. Take all rows of those 500 notes from Notes, Note Status and all 9 Ratings files.

Result: 500 notes on 500 tweets, written Oct 5 to Oct 12, with 43,656 ratings in total.

`dataset/helpful/` is an older version: 500 random Helpful notes from all years, built with only 2 of the 9 ratings files.

## How to run

You need Python 3.10 or newer. Install the packages with:

```
pip install -r requirements.txt
```

For the scripts that use the X API, create a file named `.env` with your key:

```
X_API=your_bearer_token
```

Then:

```
python build_helpful_dataset.py                    # build the dataset (uses the X API)
python build_helpful_dataset.py --no-tweets        # test run, does not use the X API
python check_dataset.py dataset/recent_helpful     # check the dataset
python find_tweet_data.py 2109031558967615703      # all data about one tweet
python get_tweet.py 2109031558967615703            # one tweet from the X API
```

To change the dates, the number of notes or the must-have note, edit `settings.py`.

Reading tweets from the X API costs about $0.005 per tweet. Building the dataset reads the 43 GB of ratings twice, so it takes 30 to 60 minutes.

## Limits

- Notes from the last days of the range have fewer ratings, because people were still rating them when X made the download.
- The tweet language comes from X's own label.
- Tweets that were deleted or private were skipped.
- `tweet_author_id` is exact for 494 of the 500 tweets. For 6 tweets it was rounded by an old bug in the tweet cache.
