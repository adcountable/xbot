import feedparser
import requests
from bs4 import BeautifulSoup

MACRO_FEEDS = [
    # Macro / markets
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://reuters.com/rssFeed/businessNews",
    "https://finance.yahoo.com/news/rssindex",
    # Bitcoin
    "https://bitcoinmagazine.com/.rss/full/",
    "https://news.bitcoin.com/feed/",
    "https://cointelegraph.com/rss",
    # Crypto markets
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.theblock.co/rss.xml",
    "https://decrypt.co/feed",
]

CONSPIRACY_FEEDS = [
    "https://www.zerohedge.com/fullrss2.xml",
    "https://activistpost.com/feed",
    "https://www.globalresearch.ca/feed",
]


def fetch_drudge_headlines(limit=15) -> list[dict]:
    """Scrape top headlines + links from Drudge Report."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        r = requests.get("https://www.drudgereport.com", headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if len(text) > 20 and href.startswith("http"):
                items.append({"title": text, "url": href})
        return items[:limit]
    except Exception as e:
        print(f"[sources] Drudge scrape failed: {e}")
        return []


def fetch_all_headlines() -> list[dict]:
    """Fetch all headlines from all sources. Returns list of {title, url, source}."""
    items = []

    for url in MACRO_FEEDS + CONSPIRACY_FEEDS:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)
        for entry in feed.entries[:6]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "")
            if title:
                items.append({"title": title, "url": link, "source": source})

    # Drudge
    for item in fetch_drudge_headlines():
        items.append({"title": item["title"], "url": item["url"], "source": "Drudge Report"})

    return items
