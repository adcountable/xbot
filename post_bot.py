"""Posts anti-ragebait Bitcoin/finance takes to X on a schedule."""

import io
import tweepy
import anthropic
import random
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY

MODES = [
    ("BULLISH TRUTH", "Make a compelling, specific, data-backed bullish case for Bitcoin. Use hard numbers, historical facts, supply scarcity, macro context, or institutional adoption. Examples: 'Only 21 million Bitcoin. 56 million millionaires worldwide. The math doesn't care about your timeline.' / 'Bitcoin has survived Mt. Gox, 3 China bans, FTX, and a 90% drawdown. It's been declared dead 474 times. Still here.'"),
    ("FUD KILLER — energy", "Destroy the 'Bitcoin uses too much energy' FUD with facts. The global banking system uses 2.5x more. Gold mining uses more. Energy securing a neutral borderless network isn't waste."),
    ("FUD KILLER — speculation", "Destroy the 'Bitcoin is just speculation' FUD. It has 15 years of price history, $1T+ market cap, ETFs, sovereign adoption, and a fixed supply. Define speculation."),
    ("FUD KILLER — ban", "Destroy the 'governments will ban it' FUD. China banned it 4 times. Hash rate hit ATH after each. US made it a strategic reserve asset. You can't ban math."),
    ("FUD KILLER — volatility", "Destroy the 'Bitcoin is too volatile' FUD. Every 4-year holding period in Bitcoin history has been profitable. Volatility is not risk if your time horizon is right."),
    ("FUD KILLER — too late", "Destroy the 'it's too late to buy Bitcoin' FUD. People said this at $1k, $10k, $20k, $30k. Global adoption is at 4%. The internet was 'too late' at 4% too."),
    ("COMPARISON — S&P 500", "Compare Bitcoin vs S&P 500. S&P returns ~10%/year. Bitcoin returned 60%+ annually since 2013. Be specific with numbers and ruthless with the conclusion."),
    ("COMPARISON — gold", "Compare Bitcoin vs gold. Gold returns 1.5%/year after inflation over 50 years. Bitcoin has returned 200x in 10 years. Gold requires vaults. Bitcoin requires a brain."),
    ("COMPARISON — real estate", "Compare Bitcoin vs real estate. Real estate needs down payments, mortgages, taxes, maintenance, agents. Bitcoin needs an internet connection. Compare returns per unit of friction."),
    ("COMPARISON — savings account", "Compare Bitcoin vs savings accounts. Average savings APY is 0.5%. Inflation is 3-4%. Cash in a savings account loses purchasing power every single day."),
    ("COMPARISON — bonds", "Compare Bitcoin vs bonds. 10-year Treasury yields ~4%. Bitcoin's worst 4-year period still beat bonds. One is a loan to a government printing money. The other has a fixed supply."),
    ("COMPARISON — hedge funds", "Compare Bitcoin vs hedge funds. Hedge funds charge 2-and-20 and underperform the S&P 80% of the time. Bitcoin has outperformed every major hedge fund index every 4-year period since 2013."),

    # Price predictions
    ("PRICE PREDICTION — cycle", "Make a bold but reasoned Bitcoin price prediction based on historical halving cycles. The 4-year cycle has played out 3 times. Each halving has preceded a new ATH within 12-18 months. Be specific about the pattern and what it implies."),
    ("PRICE PREDICTION — adoption", "Make a price prediction based on adoption curves. Global crypto adoption is ~4%. When it hits 10%, 20%, 50% — what does Bitcoin's fixed supply mean for price? Use internet/mobile adoption as a comparable S-curve."),
    ("PRICE PREDICTION — institutional", "Make a price prediction based on institutional and sovereign adoption. BlackRock, Fidelity, sovereign wealth funds, and nation-states are now buyers. Model what happens to a 21M supply asset when institutions allocate even 1-2% of AUM."),

    # Financial freedom
    ("FINANCIAL FREEDOM — banks", "Write about how Bitcoin gives financial freedom from banks. No account freezes, no permission needed, no business hours, no borders, no inflation of your savings by someone else's money printer."),
    ("FINANCIAL FREEDOM — inflation", "Write about Bitcoin as protection from inflation and monetary debasement. The dollar has lost 97% of its purchasing power since 1913. Bitcoin's supply is fixed at 21 million forever. One of these was designed for you. The other wasn't."),
    ("FINANCIAL FREEDOM — sovereignty", "Write about Bitcoin as financial sovereignty. For the first time in history, you can be your own bank. No intermediary can freeze your funds, confiscate your savings, or devalue your wealth through money printing."),
    ("FINANCIAL FREEDOM — unbanked", "Write about Bitcoin empowering the unbanked. 1.4 billion people have no access to banking. Bitcoin requires only a phone and internet. No credit check, no minimum balance, no government approval. This is what financial inclusion actually looks like."),
    ("FINANCIAL FREEDOM — censorship", "Write about Bitcoin's censorship resistance. Governments and payment processors freeze accounts, deplatform people, and cut off financial access for political reasons. Bitcoin transactions cannot be stopped, reversed, or censored by anyone — no bank, no government, no corporation. Use different real-world examples each time: PayPal deplatforming, sanctions, asset seizures, banking the unbanked, wire transfer holds."),
]

BASE_RULES = """
Write a single tweet under 280 chars.
You are a real person with strong opinions — not a content creator, not a brand.
Voice examples to emulate:
- "lol people still think the s&p is the safe play"
- "your bank account is bleeding out slowly. congrats"
- "21 million. that's it. that's the tweet"
- "institutions didn't buy bitcoin to be nice. they bought it because they did the math"
- "every bear market felt like the end. none of them were"

Rules:
- Occasionally use lowercase for casual effect
- Short is better. 1-2 sentences hits harder than 4
- Sometimes be a little sarcastic or blunt
- Vary wildly: facts, hot takes, sarcasm, short punchy observations
- No emojis. No hashtags. No "thread". No "DYOR". No "to the moon". No "Let that sink in." No "The reality is"
- NEVER mention Canada, Canadian truckers, or the freedom convoy
- Just write the tweet. No label, no preamble, no explanation."""


def generate_tweet() -> str:
    mode_name, mode_instruction = random.choice(MODES)

    # 50% of posts are sentiment-informed
    if random.random() < 0.5:
        try:
            from sentiment import fetch_recent_btc_tweets, analyze_sentiment, get_sentiment_informed_tweet
            tweets = fetch_recent_btc_tweets(total=40)
            if tweets:
                sentiment_data = analyze_sentiment(tweets)
                print(f"[post_bot] Sentiment: {sentiment_data['sentiment']} | narratives: {sentiment_data['top_narratives']}")
                return get_sentiment_informed_tweet(sentiment_data, mode_instruction, BASE_RULES)
        except Exception as e:
            print(f"[post_bot] Sentiment fetch failed, posting without: {e}")

    # Fallback: standard tweet
    prompt = f"You are a sharp, bullish Bitcoin commentator.\n\nYour task: {mode_instruction}\n{BASE_RULES}"
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def post_tweet(text: str, media_id=None):
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    kwargs = {"text": text}
    if media_id:
        kwargs["media_ids"] = [media_id]
    response = client.create_tweet(**kwargs)
    print(f"[post_bot] Posted tweet ID: {response.data['id']}")


def run():
    from chart_bot import fetch_btc_data, build_chart
    tweet = generate_tweet()
    print(f"[post_bot] Generated: {tweet}")

    media_id = None
    if random.random() < 0.2:  # 20% of posts include a chart
        try:
            data  = fetch_btc_data(days=7)
            img   = build_chart(data)
            auth  = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
            api   = tweepy.API(auth)
            media = api.media_upload(filename="btc.png", file=io.BytesIO(img))
            media_id = media.media_id
            print("[post_bot] Chart attached")
        except Exception as e:
            print(f"[post_bot] Chart failed (posting without): {e}")

    post_tweet(tweet, media_id)


if __name__ == "__main__":
    run()
