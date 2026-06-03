"""Finds high-engagement Bitcoin tweets and replies with sharp takes."""

import tweepy
import anthropic
import random
import traceback
from config import (
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
    ANTHROPIC_API_KEY, X_BEARER_TOKEN,
)

SEARCH_QUERIES = [
    # Bitcoin specific
    "#Bitcoin -is:retweet lang:en",
    "$BTC -is:retweet lang:en",
    "bitcoin price -is:retweet lang:en",
    "bitcoin dead -is:retweet lang:en",
    "bitcoin bubble -is:retweet lang:en",
    "bitcoin too late -is:retweet lang:en",
    "sell bitcoin -is:retweet lang:en",
    "crypto crash -is:retweet lang:en",
    # Lifestyle / retirement finance — high engagement, ripe for Bitcoin angle
    "quit the 9-5 -is:retweet lang:en",
    "enough to retire -is:retweet lang:en",
    "financial freedom -is:retweet lang:en",
    "passive income -is:retweet lang:en",
    "retire early -is:retweet lang:en",
    "stock market -is:retweet lang:en",
    "invested right -is:retweet lang:en",
    "beat inflation -is:retweet lang:en",
    "savings account -is:retweet lang:en",
    "real estate investment -is:retweet lang:en",
    "index funds -is:retweet lang:en",
    # Affordability / cost of living
    "can't afford a house -is:retweet lang:en",
    "cost of living -is:retweet lang:en",
    "housing prices -is:retweet lang:en",
    "middle class -is:retweet lang:en",
    "inflation is killing -is:retweet lang:en",
    "k shaped economy -is:retweet lang:en",
]

REPLY_RULES = """
You are a sharp, contrarian Bitcoin commentator replying to a tweet.
Your style: short, dry, a little sarcastic — you challenge the premise without being a jerk.
Think: smart guy at the bar who's heard this take before and has a one-liner ready.

Examples of the vibe:
- Tweet: "$250k invested is enough to quit your job" → Reply: "I suppose if you want to live in Thailand off $500/month"
- Tweet: "Bitcoin is too volatile to be a store of value" → Reply: "so is your salary after inflation. at least one of them goes up."
- Tweet: "I'm waiting for Bitcoin to drop before I buy" → Reply: "you said that at $10k too"
- Tweet: "stocks are safer than crypto" → Reply: "tell that to anyone who held Enron, Lehman, or Bed Bath & Beyond"
- Tweet: "I can't afford a house" → Reply: "real estate is the one asset that gets praised for being out of reach"
- Tweet: "cost of living is up again" → Reply: "the printer didn't print this problem away. shocking."

Rules:
- 1-2 sentences MAX. Shorter is almost always better.
- Dry wit over aggression. Confident, not angry.
- Challenge the assumption, expose the flaw, or add the missing context they ignored.
- Occasionally use lowercase for casual effect.
- No emojis. No hashtags. No "actually". No "well technically".
Just write the reply — nothing else."""


def get_client():
    kwargs = dict(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    if X_BEARER_TOKEN:
        kwargs["bearer_token"] = X_BEARER_TOKEN
    return tweepy.Client(**kwargs)


def find_tweet_to_reply():
    """Find a recent high-engagement tweet to reply to."""
    client = get_client()
    query = random.choice(SEARCH_QUERIES)
    print(f"[reply_bot] Query: {query}")

    results = client.search_recent_tweets(
        query=query,
        max_results=10,
        tweet_fields=["public_metrics", "author_id", "text"],
        expansions=["author_id"],
    )

    if not results.data:
        print(f"[reply_bot] No results for query: {query}")
        return None

    print(f"[reply_bot] Got {len(results.data)} results")

    # Pick tweet with most engagement (gracefully handle missing metrics)
    def engagement(t):
        m = t.public_metrics or {}
        return m.get("like_count", 0) + m.get("retweet_count", 0) * 2

    tweets = sorted(results.data, key=engagement, reverse=True)
    top = tweets[0]
    print(f"[reply_bot] Top tweet ({engagement(top)} engagement): {top.text[:100]}")
    return top


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

    try:
        tweet = find_tweet_to_reply()
    except Exception as e:
        print(f"[reply_bot] Search failed: {e}")
        traceback.print_exc()
        return

    if not tweet:
        print("[reply_bot] No suitable tweet found — skipping")
        return

    try:
        reply = generate_reply(tweet.text)
    except Exception as e:
        print(f"[reply_bot] Reply generation failed: {e}")
        traceback.print_exc()
        return

    print(f"[reply_bot] Reply: {reply}")

    try:
        client = get_client()
        response = client.create_tweet(
            text=reply,
            reply={"in_reply_to_tweet_id": tweet.id}
        )
        print(f"[reply_bot] Posted reply ID: {response.data['id']}")
    except Exception as e:
        print(f"[reply_bot] Failed to post reply: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    run()
