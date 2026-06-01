"""Daily overly bullish Bitcoin $1M prediction post with monthly chart."""

import io
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime, timezone, timedelta
import tweepy
import anthropic

from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY

# Halving dates for chart markers
HALVINGS = [
    datetime(2012, 11, 28),
    datetime(2016, 7,  9),
    datetime(2020, 5,  11),
    datetime(2024, 4,  20),
]

# Target scenarios
TARGETS = [
    {"price": 1_000_000, "year": 2030, "label": "$1M by 2030", "color": "#00e676"},
    {"price": 1_000_000, "year": 2033, "label": "$1M by 2033", "color": "#ff9100"},
]


def fetch_btc_history() -> list[dict]:
    """Fetch Bitcoin price history and resample to monthly."""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    prices = r.json()["prices"]

    # Resample to monthly — keep last price of each month
    monthly = {}
    for ts, price in prices:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        key = (dt.year, dt.month)
        monthly[key] = {"date": dt, "price": price}

    return [monthly[k] for k in sorted(monthly.keys())]


def project_to_1m(current_price: float, target_year: int) -> tuple:
    """Generate exponential projection curve from current price to $1M."""
    now = datetime.now(tz=timezone.utc)
    target = datetime(target_year, 1, 1, tzinfo=timezone.utc)
    years = (target - now).days / 365.25

    # Monthly points
    dates, prices = [], []
    for i in range(int(years * 12) + 1):
        d = now + timedelta(days=i * 30.4)
        t = i / (years * 12)
        # Exponential curve with slight log-curve shape
        p = current_price * (1_000_000 / current_price) ** (t ** 0.85)
        dates.append(d)
        prices.append(p)
    return dates, prices


def build_prediction_chart(history: list[dict], current_price: float) -> bytes:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    # Historical price
    hist_dates  = [h["date"] for h in history]
    hist_prices = [h["price"] for h in history]
    ax.plot(hist_dates, hist_prices, color="#f7931a", linewidth=2, label="BTC Price (historical)", zorder=3)

    # Projection lines
    colors = ["#00e676", "#ff9100"]
    years  = [2030, 2033]
    for i, (yr, col) in enumerate(zip(years, colors)):
        pdates, pprices = project_to_1m(current_price, yr)
        ax.plot(pdates, pprices, color=col, linewidth=1.5, linestyle="--",
                label=f"$1M by {yr}", alpha=0.85, zorder=2)

    # $1M line
    ax.axhline(y=1_000_000, color="#ffffff", linewidth=0.6, linestyle=":", alpha=0.3)
    ax.text(hist_dates[0], 1_100_000, "$1,000,000", color="#ffffff", fontsize=8, alpha=0.4)

    # Halving markers
    for hv in HALVINGS:
        hv_aware = hv.replace(tzinfo=timezone.utc)
        ax.axvline(x=hv_aware, color="#7c4dff", linewidth=1, linestyle="--", alpha=0.5)
        ax.text(hv_aware, ax.get_ylim()[0] * 1.1, "halving", color="#7c4dff",
                fontsize=7, rotation=90, alpha=0.6, va="bottom")

    # Scale + style
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K" if x >= 1e3 else f"${x:.0f}"
    ))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    plt.xticks(rotation=30)

    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#888", labelsize=9)
    ax.grid(axis="y", color="#1e1e1e", linewidth=0.5)

    ax.set_title(
        f"Bitcoin → $1,000,000  |  Current: ${current_price:,.0f}",
        color="white", fontsize=14, fontweight="bold", pad=14
    )
    legend = ax.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="white", fontsize=9)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return buf.read()


def generate_prediction(current_price: float) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are an aggressively bullish Bitcoin analyst posting a chart with a $1M price target.

Current Bitcoin price: ${current_price:,.0f}

Write a SHORT caption for a monthly BTC chart showing the path to $1M (under 200 chars).
Be blunt and confident. Reference one specific catalyst (halving, institutional, dollar collapse, supply shock).
Sound like a trader, not a blogger. Occasionally use lowercase. No emojis. No hashtags.
Examples of the vibe:
- "same chart, every cycle. $1M is just the next stop."
- "halvings don't care about your feelings. chart speaks for itself."
- "supply shock incoming. this chart goes to $1M and everyone will pretend they knew."

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def get_current_price() -> float:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()["bitcoin"]["usd"]


def generate_price_call(current_price: float) -> str:
    """Generate a daily price call: today → next year → 10 years."""
    import random
    # Next year: 1.5x–3x skewed high
    next_year_mult = random.uniform(1.6, 3.2)
    next_year_price = current_price * next_year_mult
    # 10 years: always over $1.3M, up to $5M
    ten_year_price = random.uniform(1_300_000, 5_000_000)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are a blunt, unapologetically bullish Bitcoin trader.

Post a daily price call with these exact numbers:
- Today: ${current_price:,.0f}
- 1 year: ${next_year_price:,.0f}
- 10 years: ${ten_year_price:,.0f}

Make it feel like a real trader's hot take — short, direct, a little cocky.
Vary the format: sometimes 3 lines, sometimes one run-on sentence, sometimes punchy fragments.
No hedging. No "I think". No emojis. No hashtags.
Examples of the vibe:
- "btc today: $67k. this time next year: $180k. 2035: $2.4M. screenshot this."
- "today $67,000. year from now $190,000. decade from now $1.8M. save this tweet."
- "$67k now. $200k by end of next year. $3M by 2034. not a prediction, just math." """

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=130,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def post_text_tweet(text: str):
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    response = client.create_tweet(text=text)
    print(f"[prediction_bot] Posted price call ID: {response.data['id']}")


def run():
    print("[prediction_bot] Fetching BTC history...")
    history = fetch_btc_history()
    current_price = history[-1]["price"]

    print(f"[prediction_bot] Current price: ${current_price:,.0f}")

    # Post 1: $1M chart
    img = build_prediction_chart(history, current_price)
    prediction = generate_prediction(current_price)
    print(f"[prediction_bot] Prediction: {prediction}")

    auth  = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
    api   = tweepy.API(auth)
    media = api.media_upload(filename="btc_1m.png", file=io.BytesIO(img))

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    client.create_tweet(text=prediction, media_ids=[media.media_id])

    # Post 2: daily price call
    price_call = generate_price_call(current_price)
    print(f"[prediction_bot] Price call: {price_call}")
    post_text_tweet(price_call)


if __name__ == "__main__":
    run()
