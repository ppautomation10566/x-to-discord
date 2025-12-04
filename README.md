X to Discord Bot

A lightweight Python bot that fetches tweets from a specified X (Twitter) account and posts them into a Discord channel via webhook. It runs automatically on a schedule using GitHub Actions.

🚀 Features

Fetches recent tweets from a target X account using the Twitter API v2.

Filters tweets by keywords or regex (e.g. leaf, cardboard, garbage).

Avoids duplicate posts by tracking the last seen tweet ID in last_seen.txt.

Posts filtered tweets into Discord with a single embed (long URL only).

Handles X API rate limits gracefully (waits 15 minutes before retrying).

Runs on a schedule (6 AM and 6 PM Eastern) or manually via workflow dispatch.

⚙️ Setup

1. Environment Variables

The bot requires secrets stored in GitHub Actions environment (e.g. x-to-discord-env):

X_BEARER_TOKEN → Twitter API bearer token

X_USER_ID → Numeric ID of the target X account

DISCORD_WEBHOOK → Discord webhook URL

You can also use a local .env file for testing:

X_BEARER_TOKEN=your_token_here
X_USER_ID=123456789
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...

2. Dependencies

Install required packages locally:

pip install -r requirements.txt

💻 Running Locally

python app.py

This will fetch tweets, filter them, and post to your Discord webhook.

🔄 GitHub Actions Workflow

The workflow (.github/workflows/run-bot.yml) runs the bot automatically.

📖 Notes

Rate limits: If the Twitter API returns 429, the bot waits 15 minutes and retries once.

Embeds: Only the long URL is posted to Discord to avoid duplicate embeds.

Persistence: last_seen.txt ensures tweets aren’t reposted.
