require('dotenv').config();

module.exports = {
  // Telegram Bot Token
  BOT_TOKEN: process.env.BOT_TOKEN || "8345110498:AAFqE3zgyV_s5P5mqFz_SfWkgeFDdIV2M8A",

  // Admin IDs - can be set in environment variables as comma-separated values, e.g. ADMINS=123,456
  ADMINS: process.env.ADMINS 
    ? process.env.ADMINS.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id))
    : [],

  // SQLite database filename
  DB_NAME: "open_budget.db",

  // Financial settings
  VOTE_REWARD: 5000,
  REFERRAL_REWARD: 1000,
  MIN_WITHDRAW: 10000,

  // Default project link
  DEFAULT_PROJECT_URL: "http://127.0.0.1:5000"
};
