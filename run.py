"""Main scheduler — runs post_bot and digest_bot on their configured schedules."""

import schedule
import time
import traceback

from config import POST_TIMES, DIGEST_TIME
import post_bot
import digest_bot


def safe(fn):
    try:
        fn()
    except Exception:
        traceback.print_exc()


for t in POST_TIMES:
    schedule.every().day.at(t.strip()).do(safe, post_bot.run)
    print(f"[scheduler] X post scheduled at {t.strip()}")

schedule.every().day.at(DIGEST_TIME).do(safe, digest_bot.run)
print(f"[scheduler] Email digest scheduled at {DIGEST_TIME}")

print("[scheduler] Running. Press Ctrl+C to stop.\n")
while True:
    schedule.run_pending()
    time.sleep(30)
