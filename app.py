import os
import requests
import time
import re
from dotenv import load_dotenv

# Load environment variables from .env (for local development)
load_dotenv()

# Environment variables
BEARER = os.getenv("X_BEARER_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
USER_ID = os.getenv("X_USER_ID")  # numeric ID of target account

if not all([BEARER, DISCORD_WEBHOOK, USER_ID]):
    raise RuntimeError("Missing required environment variables")

# --- Keywords/regex filter ---
KEYWORDS_FILE = "keywords.txt"

def load_keywords():
    """Read keywords from keywords.txt, one per line."""
    if not os.path.exists(KEYWORDS_FILE):
        raise RuntimeError(f"Keywords file {KEYWORDS_FILE} not found")
    with open(KEYWORDS_FILE, "r") as f:
        # strip whitespace, ignore empty lines
        return [line.strip() for line in f if line.strip()]

KEYWORDS = load_keywords()
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
        print("Rate limit hit. Waiting 15 minutes before retrying once...", flush=True)
        time.sleep(15 * 60)  # wait 15 minutes
        # retry once
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            print("Still rate limited after retry. Exiting.")
            return []
    resp.raise_for_status()
    return resp.json().get("data", [])

def format_tweet(tweet):
    urls = tweet.get("entities", {}).get("urls", [])
    if urls:
        return urls[0].get("expanded_url", tweet.get("text", ""))
    return tweet.get("text", "")

def post_to_discord(message):
    """Send a message to Discord via webhook."""
    r = requests.post(DISCORD_WEBHOOK, json={"content": message})
    if r.status_code >= 400:
        print(f"Discord post failed: {r.status_code} {r.text}", flush=True)

def main():
    """Main function: fetch tweets, filter, and post to Discord."""
    last_seen = get_last_seen()
    tweets = get_tweets()

    for tweet in reversed(tweets):  # oldest first
        tid = tweet.get("id")
        text = tweet.get("text", "")

        if not tid:
            continue

        # Skip already-seen tweets
        try:
            if last_seen and int(tid) <= int(last_seen):
                continue
        except ValueError:
            # corrupted last_seen.txt, ignore
            print(f"Cache corrupted", flush=True)

            pass

        # Filter by keywords
        if int(tid) > int(last_seen) and REGEX.search(text):
            expanded = format_tweet(tweet)
            post_to_discord(expanded)
            print(f"Updating last seen to {tid}", flush=True)
            set_last_seen(tid)   # update cache after posting

if __name__ == "__main__":
    main()
