# X Community Notes Dataset

This project works with data from X Community Notes. Community Notes is X's system where users add notes to posts that may be misleading. Other users rate the notes, and an algorithm decides if a note is shown under the post.

X shares all notes, ratings and note statuses as public data. This project uses that data together with the X API to build a clean dataset for research.

This is part of my work as a Graduate Research Assistant at Georgia State University.

## What this project does

1. Builds a dataset of **500 random Helpful notes** whose tweets are in **English**.
   - The notes are in all 3 datasets: Notes, Note Status and Ratings.
   - The tweet text comes from the X API.
2. Finds **all data about one tweet** across the Community Notes datasets.
3. Checks that the 500-note dataset is correct.

## The data

The raw data comes from X: https://communitynotes.x.com/guide/en/under-the-hood/download-data

It is not in this repository because it is too big (more than 10 GB). To run the code, download it and put it in a `data` folder like this:

```
data/
├── notes/notes-00000.tsv ... notes-00004.tsv
├── ratings/ratings-00000.tsv ... (one or more ratings files)
├── noteStatusHistory-00000.tsv
├── note_request.tsv
└── user_enrollment.tsv
```

The datasets are connected by IDs:

- `noteId` connects Notes, Note Status and Ratings
- `tweetId` connects a note to its tweet
- `participantId` connects a person to User Enrollment

Each note has two labels:

- **classification1**: the writer's label on the tweet (misleading or not misleading)
- **classification2**: the algorithm's label on the note (Helpful, Not Helpful, or Needs More Ratings)

## Files

| File | What it does |
|---|---|
| `build_helpful_dataset.py` | Builds the 500 Helpful notes dataset in `dataset/helpful/` |
| `find_tweet_data.py` | Finds all data about one tweet and saves it in `dataset/tweet_<tweetId>/` |
| `check_dataset.py` | Checks the `dataset/helpful/` files and prints PASS or FAIL |
| `get_tweet.py` | Gets one tweet from the X API (useful to test the API key) |
| `x_api.py` | Functions to get tweets from the X API, used by the other scripts |
| `dataset/tweet_cache.csv` | Every tweet already read from the X API, so we do not pay twice |

## The 500 Helpful notes dataset (`dataset/helpful/`)

| File | One row is |
|---|---|
| `notes.csv` | one note |
| `note_status.csv` | the status of one note |
| `ratings.csv` | one person's rating of one note |
| `tweets.csv` | one tweet (from the X API) |
| `combined.csv` | one note with its tweet, both labels and rating counts |

How it is made:

1. Find the notes that are Helpful in Note Status, are in Notes, and have Ratings.
2. Put them in a random order (seed 42, so the result is the same every time).
3. Get each note's tweet from the X API. Keep the note only if the tweet still exists and is in English. Stop at 500 notes.
4. Take the rows of those 500 notes from Notes, Note Status and Ratings.

## How to run

You need Python 3. Install the packages with:

```
pip install -r requirements.txt
```

For the scripts that use the X API, create a file named `.env` with your key:

```
X_API=your_bearer_token
```

Then:

```
python build_helpful_dataset.py
python check_dataset.py
python find_tweet_data.py 2109031558967615703 --no-ratings
python get_tweet.py 2109031558967615703
```

Reading tweets from the X API costs about $0.005 per tweet.

## Limits

- Only 2 of the 9 ratings files were used, so rating counts are partial.
- The tweet language comes from X's own label.
- Tweets that were deleted or private were skipped.
- One note in `dataset/helpful/` was added by hand (`MANUAL-2109031558967615703`) because X had not published it yet.
