"""Evening posts: Bitcoin retirement calculator + nightly sentiment prediction."""

import json
import random
import requests
import tweepy
import anthropic

from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY

RETIREMENT_SCENARIOS = [
    {"location": "Miami",          "lifestyle": "comfortable",  "annual": 120_000},
    {"location": "Bali",           "lifestyle": "luxurious",    "annual": 60_000},
    {"location": "Austin",         "lifestyle": "comfortable",  "annual": 100_000},
    {"location": "Lisbon",         "lifestyle": "luxurious",    "annual": 70_000},
    {"location": "New York City",  "lifestyle": "modest",       "annual": 150_000},
    {"location": "Chiang Mai",     "lifestyle": "comfortable",  "annual": 36_000},
    {"location": "Dubai",          "lifestyle": "luxurious",    "annual": 200_000},
    {"location": "Nashville",      "lifestyle": "comfortable",  "annual": 90_000},
    {"location": "Tokyo",          "lifestyle": "comfortable",  "annual": 80_000},
    {"location": "Puerto Rico",    "lifestyle": "luxurious",    "annual": 100_000},
    {"location": "anywhere",       "lifestyle": "never work again", "annual": 250_000},
    {"location": "a beach somewhere", "lifestyle": "doing nothing", "annual": 50_000},
]


def get_btc_price() -> float:
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        timeout=15
    )
    return r.json()["bitcoin"]["usd"]


def post_retirement_calc(btc_price: float):
    """Post a daily Bitcoin retirement calculator take."""
    scenario = random.choice(RETIREMENT_SCENARIOS)
    annual   = scenario["annual"]
    location = scenario["location"]
    lifestyle = scenario["lifestyle"]

    # At current price
    btc_needed_now = (annual * 25) / btc_price  # 25x rule (4% withdrawal)

    # At $500k BTC
    btc_at_500k = (annual * 25) / 500_000

    # At $1M BTC
    btc_at_1m = (annual * 25) / 1_000_000

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You're a blunt Bitcoin commentator posting a retirement reality check.

Scenario: {lifestyle} retirement in {location} on ${annual:,}/year
Numbers (using 4% withdrawal rule, 25x annual):
- At today's price (${btc_price:,.0f}): need {btc_needed_now:.2f} BTC
- At $500k BTC: need {btc_at_500k:.3f} BTC
- At $1M BTC: need {btc_at_1m:.4f} BTC

Write a punchy tweet (under 260 chars) with these exact numbers.
Make the point that the window to accumulate is closing.
Casual, a bit provocative. Vary the format — sometimes direct numbers, sometimes storytelling.
No emojis. No hashtags. Don't start with "Bitcoin".
Examples of the vibe:
- "to retire in bali on $60k/year you need 22 BTC today. at $1M bitcoin? 1.5 BTC. the math rewards early action."
- "comfortable retirement in miami = $3M. at today's price that's 44 BTC. at $1M bitcoin it's 3 BTC. same destination, very different ticket price." """

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=130,
        messages=[{"role": "user", "content": prompt}],
    )
    tweet = msg.content[0].text.strip()
    print(f"[night_bot] Retirement post: {tweet}")
    _post(tweet)


def post_sentiment_prediction():
    """Scrape BTC tweets, analyze sentiment, post nightly prediction."""
    from sentiment import fetch_recent_btc_tweets, analyze_sentiment

    tweets = fetch_recent_btc_tweets(total=50)
    if not tweets:
        print("[night_bot] No tweets found for sentiment")
        return

    sentiment = analyze_sentiment(tweets)
    print(f"[night_bot] Sentiment: {sentiment['sentiment']} | fear: {sentiment['fear_score']} | greed: {sentiment['greed_score']}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You're a Bitcoin trader posting your nightly market read.

Today's market sentiment: {sentiment['sentiment'].upper()}
Fear score: {sentiment['fear_score']}/100
Greed score: {sentiment['greed_score']}/100
What people are saying: {', '.join(sentiment['top_narratives'])}
Dominant emotion: {sentiment['dominant_emotion']}

Write a nightly sentiment post + bold prediction for tomorrow (under 260 chars).
Be confident and specific — give an actual directional call.
Casual tone, sounds like a real trader signing off for the night.
No emojis. No hashtags.
Examples:
- "market's in full panic mode tonight. fear this high usually means one thing. watching for reversal at open."
- "everyone's greedy right now. historically that's when you tighten up. tomorrow will be interesting."
- "sentiment sitting at max fear. this is where bitcoin is bought, not sold. see you on the other side." """

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=130,
        messages=[{"role": "user", "content": prompt}],
    )
    tweet = msg.content[0].text.strip()
    print(f"[night_bot] Sentiment prediction: {tweet}")
    _post(tweet)


def _post(text: str):
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    response = client.create_tweet(text=text)
    print(f"[night_bot] Posted tweet ID: {response.data['id']}")


def run_retirement():
    btc_price = get_btc_price()
    post_retirement_calc(btc_price)


def run_sentiment():
    post_sentiment_prediction()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sentiment":
        run_sentiment()
    else:
        run_retirement()
