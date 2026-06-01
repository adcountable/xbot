"""Sends a daily SMS with top 3 viral + top 3 emerging headlines via email-to-SMS."""

import json
import smtplib
from email.mime.text import MIMEText
import anthropic
from datetime import date

from config import ANTHROPIC_API_KEY, EMAIL_FROM, EMAIL_APP_PASSWORD, PHONE_NUMBER
from sources import fetch_all_headlines

SMS_GATEWAY = f"{PHONE_NUMBER}@tmomail.net"

CATEGORY_EMOJI = {
    "bitcoin":    "₿",
    "macro":      "🌍",
    "crypto":     "📈",
    "fed":        "🏦",
    "conspiracy": "🔍",
    "geopolitics":"🌐",
    "markets":    "📊",
    "emerging":   "⚡",
}


def _curate(headlines: list[dict]) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    headline_text = "\n".join(
        f"{i+1}. {h['title']}" for i, h in enumerate(headlines)
    )

    prompt = f"""You are a sharp macro and crypto analyst scanning today's news.

From the headlines below identify:
VIRAL (3): Already trending across multiple outlets — big mainstream stories.
EMERGING (3): Early signal only — new narrative forming, not yet mainstream. What will everyone be talking about in 48 hours?

For each item return:
- category: one word (bitcoin, macro, crypto, fed, conspiracy, geopolitics, markets)
- headline: punchy rewrite under 40 chars
- detail: ONE specific sentence — include numbers, names, or data points if available. Be concrete not vague.

Respond ONLY in this exact JSON:
{{
  "viral": [
    {{"category": "bitcoin", "headline": "...", "detail": "..."}},
    {{"category": "macro", "headline": "...", "detail": "..."}},
    {{"category": "markets", "headline": "...", "detail": "..."}}
  ],
  "emerging": [
    {{"category": "conspiracy", "headline": "...", "detail": "..."}},
    {{"category": "bitcoin", "headline": "...", "detail": "..."}},
    {{"category": "macro", "headline": "...", "detail": "..."}}
  ]
}}

Headlines:
{headline_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _send_sms(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = SMS_GATEWAY
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_FROM, SMS_GATEWAY, msg.as_string())


def run():
    print("[digest_bot] Fetching headlines...")
    headlines = fetch_all_headlines()

    print(f"[digest_bot] Curating {len(headlines)} headlines with Claude...")
    data = _curate(headlines)

    today = date.today().strftime("%b %d")

    # Send one SMS per headline
    for item in data["viral"]:
        emoji = CATEGORY_EMOJI.get(item["category"], "📌")
        subject = f"X UPDATE — {item['category'].upper()}"
        body    = f"{emoji} {item['headline']}\n{item['detail']}"
        _send_sms(subject, body)

    for item in data["emerging"]:
        emoji = CATEGORY_EMOJI.get(item["category"], "📌")
        subject = f"X UPDATE — EMERGING {item['category'].upper()}"
        body    = f"⚡ {item['headline']}\n{item['detail']}"
        _send_sms(subject, body)

    print(f"[digest_bot] {len(data['viral']) + len(data['emerging'])} SMS sent to {PHONE_NUMBER}")


if __name__ == "__main__":
    run()
