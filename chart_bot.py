"""Posts a daily Bitcoin candlestick chart with AI analysis to X."""

import io
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timezone
import tweepy
import anthropic

from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, ANTHROPIC_API_KEY


def fetch_btc_data(days=30) -> dict:
    """Fetch Bitcoin OHLC + price summary from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    ohlc = r.json()

    url2 = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
    r2 = requests.get(url2, timeout=15)
    price_data = r2.json()["bitcoin"]

    return {
        "ohlc": ohlc,
        "price": price_data["usd"],
        "change_24h": price_data["usd_24h_change"],
        "volume_24h": price_data["usd_24h_vol"],
    }


def build_chart(data: dict) -> bytes:
    """Generate a professional candlestick chart with volume + MAs."""
    ohlc = data["ohlc"]

    df = pd.DataFrame(ohlc, columns=["timestamp", "Open", "High", "Low", "Close"])
    df["Date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("Date").drop(columns=["timestamp"])
    df["Volume"] = 1000  # CoinGecko OHLC doesn't include volume — placeholder

    # Dark theme style
    mc = mpf.make_marketcolors(
        up="#00c853", down="#ff5252",
        edge="inherit",
        wick={"up": "#00c853", "down": "#ff5252"},
        volume={"up": "#00c85355", "down": "#ff525255"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#0d1117",
        edgecolor="#333",
        figcolor="#0d1117",
        gridcolor="#1a1a2e",
        gridstyle="--",
        gridaxis="horizontal",
        y_on_right=True,
        rc={"axes.labelcolor": "#888", "xtick.color": "#888", "ytick.color": "#888"},
    )

    # Add 7-day and 21-day MAs
    ma7  = df["Close"].rolling(7).mean()
    ma21 = df["Close"].rolling(21).mean()
    apds = [
        mpf.make_addplot(ma7,  color="#f7931a", width=1.2, label="MA7"),
        mpf.make_addplot(ma21, color="#7c4dff", width=1.2, label="MA21"),
    ]

    change = data["change_24h"]
    arrow  = "▲" if change >= 0 else "▼"
    title  = f"BTC/USD  ${data['price']:,.0f}  {arrow} {abs(change):.1f}%  (30d)"

    buf = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        style=style,
        title=title,
        volume=False,
        addplot=apds,
        figsize=(12, 6),
        savefig=dict(fname=buf, format="png", dpi=150, bbox_inches="tight"),
    )
    buf.seek(0)
    return buf.read()


def generate_analysis(data: dict) -> str:
    ohlc   = data["ohlc"]
    closes = [d[4] for d in ohlc]
    high30 = max(d[2] for d in ohlc)
    low30  = min(d[3] for d in ohlc)
    change30 = ((closes[-1] - closes[0]) / closes[0]) * 100

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You're a Bitcoin trader posting your daily chart take.

Data:
- Price: ${data['price']:,.0f}
- 24h: {data['change_24h']:+.1f}%
- 30d high: ${high30:,.0f} | low: ${low30:,.0f}
- 30d performance: {change30:+.1f}%

Write a short, spicy chart caption (under 200 chars).
Sound like a real trader — blunt, confident, specific about what the chart is showing.
Occasionally lowercase. No emojis. No hashtags. Don't start with "Bitcoin"."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def post_chart():
    data     = fetch_btc_data(days=30)
    img      = build_chart(data)
    analysis = generate_analysis(data)

    auth  = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
    api   = tweepy.API(auth)
    media = api.media_upload(filename="btc_chart.png", file=io.BytesIO(img))

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    response = client.create_tweet(text=analysis, media_ids=[media.media_id])
    print(f"[chart_bot] Posted: {analysis}")
    print(f"[chart_bot] Tweet ID: {response.data['id']}")


def run():
    print("[chart_bot] Fetching BTC data...")
    post_chart()


if __name__ == "__main__":
    run()
