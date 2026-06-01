"""Posts a daily Bitcoin chart with AI analysis to X."""

import io
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
import tweepy
import anthropic

from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY


def fetch_btc_data(days=30) -> dict:
    """Fetch Bitcoin OHLC + volume from CoinGecko (free, no key needed)."""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()  # [[timestamp_ms, open, high, low, close], ...]

    url2 = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
    r2 = requests.get(url2, timeout=15)
    price_data = r2.json()["bitcoin"]

    return {
        "ohlc": data,
        "price": price_data["usd"],
        "change_24h": price_data["usd_24h_change"],
        "volume_24h": price_data["usd_24h_vol"],
    }


def build_chart(data: dict) -> bytes:
    """Generate a clean Bitcoin price chart and return as PNG bytes."""
    ohlc = data["ohlc"]
    dates  = [datetime.fromtimestamp(d[0] / 1000, tz=timezone.utc) for d in ohlc]
    closes = [d[4] for d in ohlc]
    highs  = [d[2] for d in ohlc]
    lows   = [d[3] for d in ohlc]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    # Shaded range
    ax.fill_between(dates, lows, highs, alpha=0.15, color="#f7931a")
    # Price line
    ax.plot(dates, closes, color="#f7931a", linewidth=2)

    # Style
    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#888", labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=30)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    change = data["change_24h"]
    color  = "#00c853" if change >= 0 else "#ff5252"
    arrow  = "▲" if change >= 0 else "▼"

    ax.set_title(
        f"Bitcoin  ${data['price']:,.0f}   {arrow} {abs(change):.1f}% (24h)",
        color="white", fontsize=14, fontweight="bold", pad=14
    )
    ax.set_xlabel("", color="#888")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return buf.read()


def generate_analysis(data: dict) -> str:
    """Ask Claude to write sharp chart commentary."""
    ohlc   = data["ohlc"]
    closes = [d[4] for d in ohlc]
    high30 = max(d[2] for d in ohlc)
    low30  = min(d[3] for d in ohlc)
    change30 = ((closes[-1] - closes[0]) / closes[0]) * 100

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are a sharp Bitcoin market analyst.

Current data:
- Price: ${data['price']:,.0f}
- 24h change: {data['change_24h']:+.1f}%
- 24h volume: ${data['volume_24h']:,.0f}
- 30-day high: ${high30:,.0f}
- 30-day low: ${low30:,.0f}
- 30-day performance: {change30:+.1f}%

Write a single sharp tweet (under 220 chars) analyzing the current price action.
Be specific, bullish but honest. Include a key observation about trend, support/resistance, or momentum.
No emojis. No hashtags. No "DYOR". Don't start with "Bitcoin" — vary the opening."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def post_chart():
    data     = fetch_btc_data(days=30)
    img      = build_chart(data)
    analysis = generate_analysis(data)

    # Upload image via v1.1 API
    auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
    api  = tweepy.API(auth)
    media = api.media_upload(filename="btc_chart.png", file=io.BytesIO(img))

    # Post tweet with image
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    response = client.create_tweet(text=analysis, media_ids=[media.media_id])
    print(f"[chart_bot] Posted chart tweet ID: {response.data['id']}")
    print(f"[chart_bot] Analysis: {analysis}")


def run():
    print("[chart_bot] Fetching BTC data...")
    post_chart()


if __name__ == "__main__":
    run()
