import os
import requests
import re
from dotenv import load_dotenv

# Load environment variables from .env (for local development)
load_dotenv()

# Environment variables
BEARER = os.getenv("X_BEARER_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
USER_ID = os.getenv("X_USER_ID")  # numeric ID of target account

# Keywords/regex filter
KEYWORDS = ["leaf", "cardboard", "garbage"]
REGEX = re.compile("|".join(KEYWORDS), re.IGNORECASE)

# Track last seen tweet
LAST_SEEN_FILE = "last_seen.txt"

def get_last_seen():
    """Read the last seen tweet ID from file."""
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r") as f:
            return f.read().strip()
    return None

def set_last_seen(tweet_id):
    """Write the last seen tweet ID to file."""
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(tweet_id)

def get_tweets():
    """Fetch recent tweets from the target user."""
    url = f"https://api.twitter.com/2/users/{USER_ID}/tweets"
    headers = {"Authorization": f"Bearer {BEARER}"}
    params = {"max_results": 5}
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 429:
        print("Rate limit hit. Waiting 15 minutes before retrying once...")
        time.sleep(15 * 60)  # wait 15 minutes
        # retry once
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            print("Still rate limited after retry. Exiting.")
            return []
    resp.raise_for_status()
    return resp.json().get("data", [])


def post_to_discord(text, url=None):
    """Send a message to Discord via webhook."""
    payload = {"content": text}
    if url:
        payload["content"] += f"\n{url}"
    requests.post(DISCORD_WEBHOOK, json=payload)

def main():
    """Main function: fetch tweets, filter, and post to Discord."""
    last_seen = get_last_seen()
    tweets = get_tweets()

    for tweet in reversed(tweets):  # oldest first
        tid = tweet["id"]
        text = tweet["text"]

        # Skip already-seen tweets
        if last_seen and tid <= last_seen:
            continue

        # Filter by keywords
        if REGEX.search(text):
            post_to_discord(text, f"https://x.com/{USER_ID}/status/{tid}")
            set_last_seen(tid)

if __name__ == "__main__":
    main()