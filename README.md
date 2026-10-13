<<<<<<< HEAD
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
=======
# misinformation



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://git.insight.gsu.edu/efficiency_scaling/misinformation.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://git.insight.gsu.edu/efficiency_scaling/misinformation/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> a25e442abb159f91af6a9ecea53a773d6a7f1a53
