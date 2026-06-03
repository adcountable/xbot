"""Finds high-engagement tweets and replies with sharp contrarian takes."""

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
    # Lifestyle / retirement finance
    "quit the 9-5 -is:retweet lang:en",
    "enough to retire -is:retweet lang:en",
    "financial freedom -is:retweet lang:en",
    "passive income -is:retweet lang:en",
    "retire early -is:retweet lang:en",
    "stock market -is:retweet lang:en",
    "beat inflation -is:retweet lang:en",
    "savings account -is:retweet lang:en",
    "index funds -is:retweet lang:en",
    "real estate investment -is:retweet lang:en",
    # Affordability / cost of living
    "can't afford a house -is:retweet lang:en",
    "cost of living -is:retweet lang:en",
    "housing prices -is:retweet lang:en",
    "middle class squeeze -is:retweet lang:en",
    "inflation is killing me -is:retweet lang:en",
]

REPLY_RULES = """
You're a regular person reading this tweet and you have a one-liner response. Not trying to go viral, not trying to educate anyone. Just saying the thing that immediately came to mind.

Good reply examples:
- Tweet: "$250k invested is enough to quit your job" → "sure if you want to live in Thailand on $500/month"
- Tweet: "Bitcoin is too volatile to be a store of value" → "so is your salary after inflation. at least one of them goes up."
- Tweet: "I'm waiting for Bitcoin to drop before I buy" → "you said that at $10k too"
- Tweet: "stocks are the safe play" → "tell that to anyone who held Enron, Lehman, or Bed Bath & Beyond"
- Tweet: "I can't afford a house" → "real estate is the one asset that gets praised specifically for being out of reach"
- Tweet: "cost of living is up again" → "the printer didn't print this problem away. shocking."
- Tweet: "just put everything in index funds" → "great plan. hope the fed printer stays on."
- Tweet: "crypto is a scam" → "so is a savings account at 0.5% while inflation runs 4%. pick your scam."

What NOT to do: Don't start with "Well," or "Actually," or "Interesting take." Don't explain your reasoning. Don't write more than 2 sentences. Don't be preachy.

- No em dashes (the — character). Use a comma or period.
- No emojis. No hashtags.
Just write the reply. One or two lines max."""


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
    """Try multiple queries until we find a replyable tweet."""
    client = get_client()

    # Shuffle queries and try up to 6 before giving up
    queries = random.sample(SEARCH_QUERIES, min(6, len(SEARCH_QUERIES)))

    for query in queries:
        print(f"[reply_bot] Trying query: {query}")
        try:
            results = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["public_metrics", "author_id", "text", "reply_settings"],
                expansions=["author_id"],
            )
        except Exception as e:
            print(f"[reply_bot] Search error on '{query}': {e}")
            continue

        if not results.data:
            print(f"[reply_bot] No results — trying next query")
            continue

        # Filter out tweets with restricted replies
        open_tweets = [
            t for t in results.data
            if getattr(t, "reply_settings", "everyone") in ("everyone", None, "")
        ]

        if not open_tweets:
            print(f"[reply_bot] All tweets are reply-restricted — trying next query")
            continue

        print(f"[reply_bot] {len(open_tweets)} open tweets found")

        def engagement(t):
            m = t.public_metrics or {}
            return m.get("like_count", 0) + m.get("retweet_count", 0) * 2

        top = sorted(open_tweets, key=engagement, reverse=True)[0]
        print(f"[reply_bot] Selected (engagement={engagement(top)}): {top.text[:100]}")
        return top

    print("[reply_bot] Exhausted all queries — no suitable tweet found")
    return None


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
    print("[reply_bot] Starting...")

    try:
        tweet = find_tweet_to_reply()
    except Exception as e:
        print(f"[reply_bot] Search crashed: {e}")
        traceback.print_exc()
        return

    if not tweet:
        return

    try:
        reply = generate_reply(tweet.text)
    except Exception as e:
        print(f"[reply_bot] Claude failed: {e}")
        traceback.print_exc()
        return

    print(f"[reply_bot] Reply: {reply}")

    try:
        client = get_client()
        response = client.create_tweet(
            text=reply,
            reply={"in_reply_to_tweet_id": tweet.id}
        )
        print(f"[reply_bot] ✓ Posted reply ID: {response.data['id']}")
    except Exception as e:
        print(f"[reply_bot] Post failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    run()
