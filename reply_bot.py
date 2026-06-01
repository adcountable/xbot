"""Finds high-engagement Bitcoin tweets and replies with sharp takes."""

import tweepy
import anthropic
import random
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY

SEARCH_QUERIES = [
    "#Bitcoin -is:retweet lang:en",
    "$BTC -is:retweet lang:en",
    "bitcoin price -is:retweet lang:en",
    "bitcoin dead -is:retweet lang:en",
    "bitcoin bubble -is:retweet lang:en",
    "bitcoin energy -is:retweet lang:en",
    "bitcoin too late -is:retweet lang:en",
    "sell bitcoin -is:retweet lang:en",
    "crypto crash -is:retweet lang:en",
]

REPLY_RULES = """
You are a sharp, bullish Bitcoin commentator replying to a tweet.
Write a short reply (under 200 chars) that is:
- Casual and conversational — like a smart friend responding
- Either adds a compelling data point, a contrarian angle, or a calm correction
- Never aggressive or rude — just confident and factual
- No emojis. No hashtags. No "actually" as an opener.
- Sound human, not like a bot
Just write the reply — nothing else."""


def get_client():
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )


def find_tweet_to_reply():
    """Find a recent high-engagement Bitcoin tweet to reply to."""
    client = get_client()
    query = random.choice(SEARCH_QUERIES)

    results = client.search_recent_tweets(
        query=query,
        max_results=10,
        tweet_fields=["public_metrics", "author_id", "text"],
        expansions=["author_id"],
    )

    if not results.data:
        return None

    # Pick tweet with most engagement
    tweets = sorted(
        results.data,
        key=lambda t: (
            t.public_metrics["like_count"] +
            t.public_metrics["retweet_count"] * 2
        ),
        reverse=True,
    )
    return tweets[0]


def generate_reply(tweet_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f'Tweet: "{tweet_text}"\n\n{REPLY_RULES}'
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def run():
    print("[reply_bot] Searching for tweet to reply to...")
    tweet = find_tweet_to_reply()
    if not tweet:
        print("[reply_bot] No suitable tweet found")
        return

    print(f"[reply_bot] Found: {tweet.text[:80]}...")
    reply = generate_reply(tweet.text)
    print(f"[reply_bot] Reply: {reply}")

    client = get_client()
    response = client.create_tweet(
        text=reply,
        reply={"in_reply_to_tweet_id": tweet.id}
    )
    print(f"[reply_bot] Posted reply ID: {response.data['id']}")


if __name__ == "__main__":
    run()
