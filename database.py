import sqlite3
import os
from datetime import datetime
import config

class Database:
    def __init__(self, db_name=config.DB_NAME):
        self.db_name = db_name
        self.init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER DEFAULT 0,
                    referred_by INTEGER,
                    registered_at TEXT
                )
            """)
            
            # Try to add phone_number column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            except sqlite3.OperationalError:
                pass # Already exists
            
            # Votes table
            cursor.execute("""
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
            """)
            
            # Withdrawals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    card_number TEXT,
                    amount INTEGER,
                    status TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Try to add dynamic admins table for testing
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY
                )
            """)
            
            conn.commit()
            
        # Initialize default settings if they don't exist
        self._init_setting("project_url", config.DEFAULT_PROJECT_URL)
        self._init_setting("vote_reward", str(config.VOTE_REWARD))
        self._init_setting("referral_reward", str(config.REFERRAL_REWARD))
        self._init_setting("min_withdraw", str(config.MIN_WITHDRAW))
        self._init_setting("is_bot_active", "True")

    def _init_setting(self, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_setting(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    # Admin DB-level Methods (for testing / auto-admin)
    def add_admin(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
            conn.commit()

    def is_admin(self, user_id):
        if user_id in config.ADMINS:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

    def get_admins(self):
        admins = list(config.ADMINS)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM admins")
            db_admins = [row[0] for row in cursor.fetchall()]
            for a in db_admins:
                if a not in admins:
                    admins.append(a)
        return admins

    # User Methods
    def add_user(self, user_id, username, first_name, referred_by=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if user already exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone() is None:
                # Validate referral to avoid self-referral
                if referred_by and int(referred_by) == int(user_id):
                    referred_by = None
                
                # Check if referrer exists
                if referred_by:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referred_by,))
                    if cursor.fetchone() is None:
                        referred_by = None

                cursor.execute(
                    "INSERT INTO users (user_id, username, first_name, balance, referred_by, registered_at, phone_number) VALUES (?, ?, ?, 0, ?, ?, NULL)",
                    (user_id, username, first_name, referred_by, now)
                )
                conn.commit()
                return True
        return False

    def update_user_phone(self, user_id, phone_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET phone_number = ? WHERE user_id = ?", (phone_number, user_id))
            conn.commit()

    def get_user(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, first_name, balance, referred_by, registered_at, phone_number FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "balance": row[3],
                    "referred_by": row[4],
                    "registered_at": row[5],
                    "phone_number": row[6]
                }
        return None

    def get_user_by_phone(self, phone_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, first_name, balance, referred_by, registered_at, phone_number FROM users WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "balance": row[3],
                    "referred_by": row[4],
                    "registered_at": row[5],
                    "phone_number": row[6]
                }
        return None

    def update_balance(self, user_id, amount):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()

    def get_referral_count(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
            return cursor.fetchone()[0]

    # Vote Methods
    def add_vote(self, user_id, phone_number):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO votes (user_id, phone_number, sms_code, status, created_at, updated_at) VALUES (?, ?, NULL, 'pending_phone', ?, ?)",
                (user_id, phone_number, now, now)
            )
            conn.commit()
            return cursor.lastrowid

    def add_web_vote(self, phone_number, sms_code, user_id=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO votes (user_id, phone_number, sms_code, status, created_at, updated_at) VALUES (?, ?, ?, 'pending_sms', ?, ?)",
                (user_id, phone_number, sms_code, now, now)
            )
            conn.commit()
            return cursor.lastrowid

    def verify_web_code(self, phone_number, sms_code):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Find the latest pending_sms vote for this phone number
            cursor.execute(
                "SELECT id, user_id, sms_code FROM votes WHERE phone_number = ? AND status = 'pending_sms' ORDER BY id DESC LIMIT 1",
                (phone_number,)
            )
            row = cursor.fetchone()
            if row:
                vote_id, user_id, db_code = row[0], row[1], row[2]
                if db_code == sms_code:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("UPDATE votes SET status = 'approved', updated_at = ? WHERE id = ?", (now, vote_id))
                    
                    # Reward user
                    if user_id:
                        vote_reward = int(self.get_setting("vote_reward", str(config.VOTE_REWARD)))
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (vote_reward, user_id))
                        
                        # Reward referrer
                        cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
                        ref_row = cursor.fetchone()
                        if ref_row and ref_row[0]:
                            referrer_id = ref_row[0]
                            ref_reward = int(self.get_setting("referral_reward", str(config.REFERRAL_REWARD)))
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (ref_reward, referrer_id))
                            
                    conn.commit()
                    return {"success": True, "vote_id": vote_id, "user_id": user_id}
            return {"success": False}

    def update_vote_sms(self, vote_id, sms_code):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE votes SET sms_code = ?, status = 'pending_sms', updated_at = ? WHERE id = ?",
                (sms_code, now, vote_id)
            )
            conn.commit()

    def update_vote_status(self, vote_id, status):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE votes SET status = ?, updated_at = ? WHERE id = ?", (status, now, vote_id))
            conn.commit()

    def get_vote(self, vote_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, phone_number, sms_code, status, created_at, updated_at FROM votes WHERE id = ?", (vote_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "phone_number": row[2],
                    "sms_code": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                }
        return None

    def get_pending_votes(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, phone_number, sms_code, status, created_at FROM votes WHERE status IN ('pending_phone', 'pending_sms') ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            votes = []
            for row in rows:
                votes.append({
                    "id": row[0],
                    "user_id": row[1],
                    "phone_number": row[2],
                    "sms_code": row[3],
                    "status": row[4],
                    "created_at": row[5]
                })
            return votes

    def check_active_vote_exists(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM votes WHERE user_id = ? AND status IN ('pending_phone', 'pending_sms')",
                (user_id,)
            )
            return cursor.fetchone()[0] > 0

    def check_phone_voted_already(self, phone_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM votes WHERE phone_number = ? AND status = 'approved'",
                (phone_number,)
            )
            return cursor.fetchone()[0] > 0

    def get_user_successful_votes_count(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM votes WHERE user_id = ? AND status = 'approved'",
                (user_id,)
            )
            return cursor.fetchone()[0]

    # Withdrawal Methods
    def add_withdrawal(self, user_id, card_number, amount):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO withdrawals (user_id, card_number, amount, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                (user_id, card_number, amount, now)
            )
            # Deduct balance immediately
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            return cursor.lastrowid

    def get_pending_withdrawals(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, card_number, amount, status, created_at FROM withdrawals WHERE status = 'pending' ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            withdrawals = []
            for row in rows:
                withdrawals.append({
                    "id": row[0],
                    "user_id": row[1],
                    "card_number": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "created_at": row[5]
                })
            return withdrawals

    def get_withdrawal(self, withdrawal_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, card_number, amount, status, created_at FROM withdrawals WHERE id = ?", (withdrawal_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "card_number": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "created_at": row[5]
                }
        return None

    def update_withdrawal_status(self, withdrawal_id, status):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # If rejected, refund the user
            if status == "rejected":
                cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = 'pending'", (withdrawal_id,))
                row = cursor.fetchone()
                if row:
                    user_id, amount = row[0], row[1]
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            
            cursor.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, withdrawal_id))
            conn.commit()

    # Stats Method
    def get_stats(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM votes WHERE status = 'approved'")
            approved_votes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM votes WHERE status IN ('pending_phone', 'pending_sms')")
            pending_votes = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE status = 'approved'")
            total_withdrawn = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE status = 'pending'")
            pending_withdrawn = cursor.fetchone()[0] or 0

            return {
                "total_users": total_users,
                "approved_votes": approved_votes,
                "pending_votes": pending_votes,
                "total_withdrawn": total_withdrawn,
                "pending_withdrawn": pending_withdrawn
            }

    def get_all_users_list(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

    def get_top_referrers(self, limit=10):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id, u.first_name, u.username, COUNT(r.user_id) as ref_count
                FROM users u
                INNER JOIN users r ON r.referred_by = u.user_id
                GROUP BY u.user_id
                ORDER BY ref_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            top_users = []
            for row in rows:
                top_users.append({
                    "user_id": row[0],
                    "first_name": row[1],
                    "username": row[2] if row[2] else "Yashirin",
                    "ref_count": row[3]
                })
            return top_users

    def get_top_voters(self, limit=10):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id, u.first_name, u.username, COUNT(v.id) as vote_count
                FROM users u
                INNER JOIN votes v ON v.user_id = u.user_id AND v.status = 'approved'
                GROUP BY u.user_id
                ORDER BY vote_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            top_voters = []
            for row in rows:
                top_voters.append({
                    "user_id": row[0],
                    "first_name": row[1],
                    "username": row[2] if row[2] else "Yashirin",
                    "vote_count": row[3]
                })
            return top_voters
