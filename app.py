import os
import requests
import time
from zoneinfo import ZoneInfo
from datetime import datetime
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
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r") as f:
            return f.read().strip()
    return None

def set_last_seen(tweet_id):
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(tweet_id)


def get_tweets():
    """Fetch recent tweets from the target user."""
    url = f"https://api.twitter.com/2/users/{USER_ID}/tweets"
    headers = {"Authorization": f"Bearer {BEARER}"}
    params = {
        "max_results": 3,
        "tweet.fields": "created_at"
    }
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 429:
        print("Rate limit hit. Waiting 15 minutes before retrying once...", flush=True)
        time.sleep(15 * 60)
        
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            print("Still rate limited after retry. Exiting.", flush=True)
            return []
    
    resp.raise_for_status()
    tweets = resp.json().get("data", [])

    # Logging: Eastern Time timestamp + tweet ID + first 50 chars
    for t in tweets:
        tid = t.get("id", "UNKNOWN_ID")
        ts_raw = t.get("created_at", None)

        if ts_raw:
            # Convert Twitter's UTC timestamp to Eastern Time
            ts_utc = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            ts_et = ts_utc.astimezone(ZoneInfo("America/New_York"))
            ts_str = ts_et.strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            ts_str = "UNKNOWN_TIME"

        preview = t.get("text", "")[:50].replace("\n", " ")
        print(f"[{ts_str}] [Tweet ID {tid}] {preview}", flush=True)

    return tweets


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
    last_seen = get_last_seen()
    if last_seen is None:
        last_seen = "0"

    last_seen_int = int(last_seen)
    max_seen = last_seen_int

    tweets = get_tweets()

    # Sort tweets by ID so they are oldest → newest because X API doesn't guarantee order
    tweets.sort(key=lambda t: int(t["id"]))

    for tweet in tweets:
        tid = int(tweet["id"])
        text = tweet.get("text", "")

        # Skip anything we've already processed
        if tid <= last_seen_int:
            continue

        # Keyword match → post to Discord
        if REGEX.search(text):
            expanded = format_tweet(tweet)
            post_to_discord(expanded)
            print(f"Matched keyword in Tweet ID {tid}", flush=True)

        # Advance pointer
        if tid > max_seen:
            max_seen = tid

    # Update last_seen once per run
    print(f"Updating last_seen to {max_seen}", flush=True)
    set_last_seen(str(max_seen))


if __name__ == "__main__":
    main()
