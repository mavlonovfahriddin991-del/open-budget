# Configuration settings for Open Budget Telegram Bot

import os

# Bot Token from @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8345110498:AAFqE3zgyV_s5P5mqFz_SfWkgeFDdIV2M8A")

# List of admin telegram user IDs (must be integers)
# Example: ADMINS = [123456789, 987654321]
ADMINS = []

# Database configuration
DB_NAME = "open_budget.db"

# Financial settings (in UZS or points)
VOTE_REWARD = 5000       # Amount rewarded for a verified vote
REFERRAL_REWARD = 1000   # Amount rewarded to referrer when referee votes
MIN_WITHDRAW = 10000     # Minimum withdrawal amount

# Default Open Budget project link
DEFAULT_PROJECT_URL = "http://127.0.0.1:5000"  # Points to our simulator web app!
