"""Posts anti-ragebait Bitcoin/finance takes to X on a schedule."""

import io
import sys
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

AFFORDABILITY_MODES = [
    ("AFFORDABILITY — housing vs stocks", "You're venting about the fact that the stock market is at all-time highs but 80% of Americans literally cannot afford a median-priced home. Home prices up 50% since 2020. S&P up 150%. These things happened at the same time. You find this infuriating. Short, casual, real. Could be one sentence or three fragments."),
    ("AFFORDABILITY — food prices", "You're pissed about grocery prices. Beef is up over 100% in the last decade. Trying to eat real food, quality protein, actual nutrition, costs way more than it used to. You're not quoting a report, you just went to the store. Say something real about it. Keep it short."),
    ("AFFORDABILITY — k-shaped economy", "You're thinking about how after 2020, rich people got richer and everyone else got squeezed. S&P doubled. Billionaire wealth up over a trillion. Rent up 30%. Groceries up 25%. Wages up 18%. You want to say something about that gap. Not a lecture. Just a real observation from someone who lives in the bottom half of that K."),
    ("AFFORDABILITY — retirement scam", "You're frustrated about retirement in America. 56% of people have less than $10k saved. Social Security is going to get cut. Pensions disappeared. The 401k was never designed for this. The people who set this all up are fine. You're just saying the quiet part out loud."),
    ("AFFORDABILITY — wages vs everything", "You're doing the math in your head on wages vs. cost of living and it doesn't add up. Rent up. Insurance up. Groceries up. Wages barely moved. Not a rant, just stating facts that somehow nobody in charge acknowledges. Keep it casual and specific. One or two sentences max."),
    ("AFFORDABILITY — wealth gap", "You're noticing that when the news celebrates stock market records, it's celebrating something most people have almost nothing in. Top 1% owns more than the bottom 90% combined. CEO pay is 350x the average worker. In 1980 it was 30x. Just say what you're thinking about that. Conversational. Not a speech."),
    ("AFFORDABILITY — student debt", "You're thinking about the student debt situation. $1.7 trillion in loans. Average grad owes $37k for a degree in a market that wanted 5 years experience. College costs went up 4x faster than inflation. You're not angry in a performative way, just genuinely baffled that this was the plan. Say something honest about it."),
]

BASE_RULES = """
Write one tweet under 280 chars.

You're a regular person who follows Bitcoin and finance obsessively. Not a brand, not an influencer, not a newsletter. Just someone who's been paying attention and has opinions.

Good examples of the voice:
- "21 million. thats it."
- "people who called bitcoin dead at $3k got real quiet"
- "blackrock bought $20 billion of bitcoin. just noting that."
- "your savings account is losing purchasing power every single day. but yeah keep it there"
- "same bear market panic. different cycle. same ending."
- "s&p up 150% since 2020. beef up 100%. cool."
- "median home needs $120k income to qualify. median income is $56k. but its a supply problem, sure"

What NOT to sound like (never write this):
- "Bitcoin represents a transformative shift in..."
- "It's worth noting that traditional finance..."
- "Here's why this matters:"
- "The data clearly shows..."
- "In today's financial landscape..."

Rules:
- Lowercase is fine. Fragments are fine. Trailing off is fine.
- Short almost always hits harder. If it can be 6 words, make it 6 words.
- No em dashes (the — character). Use a comma or period instead.
- No emojis. No hashtags. No "thread". No "DYOR". No "to the moon". No "Let that sink in." No "The reality is"
- NEVER mention Canada, Canadian truckers, or the freedom convoy
- Just write the tweet. No label, no preamble."""


def generate_tweet(affordability: bool = False) -> str:
    pool = AFFORDABILITY_MODES if affordability else MODES
    mode_name, mode_instruction = random.choice(pool)
    print(f"[post_bot] Mode: {mode_name}")

    # 50% of standard posts are sentiment-informed (skip for affordability)
    if not affordability and random.random() < 0.5:
        try:
            from sentiment import fetch_recent_btc_tweets, analyze_sentiment, get_sentiment_informed_tweet
            tweets = fetch_recent_btc_tweets(total=40)
            if tweets:
                sentiment_data = analyze_sentiment(tweets)
                print(f"[post_bot] Sentiment: {sentiment_data['sentiment']} | narratives: {sentiment_data['top_narratives']}")
                return get_sentiment_informed_tweet(sentiment_data, mode_instruction, BASE_RULES)
        except Exception as e:
            print(f"[post_bot] Sentiment fetch failed, posting without: {e}")

    # Standard tweet
    prompt = f"You are a sharp commentator on finance, economics, and Bitcoin.\n\nYour task: {mode_instruction}\n{BASE_RULES}"
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


def run(affordability: bool = False):
    from chart_bot import fetch_btc_data, build_chart
    tweet = generate_tweet(affordability=affordability)
    print(f"[post_bot] Generated: {tweet}")

    media_id = None
    # Affordability posts: 40% chance of chart. Standard posts: 80%.
    chart_chance = 0.4 if affordability else 0.8
    if random.random() < chart_chance:
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
    affordability = "--affordability" in sys.argv or "affordability" in sys.argv
    run(affordability=affordability)
