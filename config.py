import os
from dotenv import load_dotenv

load_dotenv(override=True)

X_API_KEY             = os.getenv("X_API_KEY", "")
X_API_SECRET          = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN        = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")

ANTHROPIC_API_KEY     = os.environ["ANTHROPIC_API_KEY"]

EMAIL_FROM            = os.getenv("EMAIL_FROM", "")
EMAIL_APP_PASSWORD    = os.getenv("EMAIL_APP_PASSWORD", "")
PHONE_NUMBER          = os.getenv("PHONE_NUMBER", "")

POST_TIMES            = os.getenv("POST_TIMES", "08:00,13:00,19:00").split(",")
DIGEST_TIME           = os.getenv("DIGEST_TIME", "07:00")
