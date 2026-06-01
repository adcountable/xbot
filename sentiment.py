"""Scrapes recent Bitcoin tweets, gauges sentiment, surfaces top narratives."""

import json
import tweepy
import anthropic
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY

SEARCH_TERMS = [
    "#Bitcoin -is:retweet lang:en",
    "$BTC -is:retweet lang:en",
    "bitcoin price -is:retweet lang:en",
]


def fetch_recent_btc_tweets(total=60) -> list[str]:
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    tweets = []
    for query in SEARCH_TERMS:
        try:
            results = client.search_recent_tweets(
                query=query,
                max_results=20,
                tweet_fields=["public_metrics", "text"],
            )
            if results.data:
                # Weight by engagement
                sorted_tweets = sorted(
                    results.data,
                    key=lambda t: t.public_metrics["like_count"] + t.public_metrics["retweet_count"] * 2,
                    reverse=True
                )
                tweets += [t.text for t in sorted_tweets[:20]]
        except Exception as e:
            print(f"[sentiment] Search failed for '{query}': {e}")
    return tweets[:total]


def analyze_sentiment(tweets: list[str]) -> dict:
    """Ask Claude to analyze Bitcoin market sentiment from tweets."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    tweet_text = "\n".join(f"- {t[:120]}" for t in tweets[:40])

    prompt = f"""Analyze the Bitcoin market sentiment from these recent tweets.

Tweets:
{tweet_text}

Return ONLY this JSON:
{{
  "sentiment": "fear" | "neutral" | "greedy" | "euphoric",
  "fear_score": 0-100,
  "greed_score": 0-100,
  "top_narratives": ["narrative 1", "narrative 2", "narrative 3"],
  "dominant_emotion": "one word",
  "content_angle": "Given this sentiment, what angle should a bullish Bitcoin account take? One sentence."
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def get_sentiment_informed_tweet(sentiment_data: dict, mode_instruction: str, base_rules: str) -> str:
    """Generate a tweet that's informed by current market sentiment."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are a sharp Bitcoin commentator.

Current market sentiment: {sentiment_data['sentiment'].upper()} (fear: {sentiment_data['fear_score']}/100, greed: {sentiment_data['greed_score']}/100)
What people are talking about: {', '.join(sentiment_data['top_narratives'])}
Content angle: {sentiment_data['content_angle']}

Your task: {mode_instruction}

Make the tweet feel timely — reference the current mood or narrative if it fits naturally.
{base_rules}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=130,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


if __name__ == "__main__":
    print("Fetching tweets...")
    tweets = fetch_recent_btc_tweets()
    print(f"Got {len(tweets)} tweets")
    sentiment = analyze_sentiment(tweets)
    print(json.dumps(sentiment, indent=2))
