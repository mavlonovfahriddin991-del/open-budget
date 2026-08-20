from flask import Flask, render_template, request, redirect, url_for, flash
import random
import requests
import config
from database import Database

app = Flask(__name__)
app.secret_key = "open_budget_mock_secret_key_12345"
db = Database()

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        print(f"Telegram API Error: {e}")
        return None

def notify_admins(text):
    admins = db.get_admins()
    for admin_id in admins:
        send_telegram_message(admin_id, text)

@app.route("/")
def index():
    project_url = db.get_setting("project_url", config.DEFAULT_PROJECT_URL)
    vote_reward = db.get_setting("vote_reward", str(config.VOTE_REWARD))
    top_voters = db.get_top_voters(10)
    top_referrers = db.get_top_referrers(10)
    return render_template(
        "index.html", 
        vote_reward=vote_reward, 
        project_url=project_url, 
        top_voters=top_voters, 
        top_referrers=top_referrers
    )

@app.route("/vote", methods=["POST"])
def vote():
    phone = request.form.get("phone", "").strip()
    
    # Clean phone number format
    phone = phone.replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("998"):
            phone = "+" + phone
        elif len(phone) == 9 and phone.isdigit():
            phone = "+998" + phone
        else:
            flash("Telefon raqami noto'g'ri shaklda. Masalan: +998901234567", "error")
            return redirect(url_for("index"))

    if not (phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit()):
        flash("Faqat O'zbekiston telefon raqamlari qabul qilinadi (+998XXXXXXXXX).", "error")
        return redirect(url_for("index"))

    # Check if already voted
    if db.check_phone_voted_already(phone):
        flash("Ushbu telefon raqam orqali avvalroq ovoz berilgan!", "error")
        return redirect(url_for("index"))

    # Generate test 6-digit SMS code
    sms_code = str(random.randint(100000, 999999))
    
    # Check if phone number is registered in the bot
    user = db.get_user_by_phone(phone)
    user_id = user["user_id"] if user else None

    # Register web vote request in db
    db.add_web_vote(phone, sms_code, user_id)

    # Simulation Logic for Sending Verification Code
    if user_id:
        # Send SMS code directly to user's Telegram!
        msg_to_user = (
            f"🗳️ **Open Budget Veb-sayti**\n\n"
            f"Siz sayt orqali ovoz berishni boshladingiz.\n"
            f"Tasdiqlash kodingiz: `{sms_code}`\n\n"
            f"Ushbu kodni veb-saytdagi oynaga kiriting."
        )
        send_telegram_message(user_id, msg_to_user)
        
        # Notify admins
        notify_admins(
            f"🌐 **Saytdan ovoz berish so'rovi!**\n"
            f"📱 Telefon: `{phone}`\n"
            f"👤 Foydalanuvchi: {user['first_name']} (ID: `{user_id}`)\n"
            f"🔑 Kod foydalanuvchining Telegramiga yuborildi."
        )
        flash("Tasdiqlash kodi Telegram botingizga yuborildi. Iltimos, kodni kiriting.", "success")
    else:
        # User not registered in bot. Send code to Admins so they can see/test it
        notify_admins(
            f"🌐 **Saytdan ovoz berish so'rovi (Botda ulanmagan raqam)!**\n"
            f"📱 Telefon: `{phone}`\n"
            f"🔑 Tasdiqlash (SMS) kod: `{sms_code}`\n\n"
            f"⚠️ Ushbu raqam botimizdan ro'yxatdan o'tmagan. Test uchun kodni ushbu yerdan olib saytga kiritishingiz mumkin."
        )
        flash("Tasdiqlash kodi yuborildi! (Loyiha test rejimida bo'lgani uchun, agar raqamingiz botga ulanmagan bo'lsa, kod bot adminlariga yuboriladi)", "info")

    return redirect(url_for("verify", phone=phone))

@app.route("/verify")
def verify():
    phone = request.args.get("phone", "")
    if not phone:
        return redirect(url_for("index"))
    return render_template("verify.html", phone=phone)

@app.route("/verify_code", methods=["POST"])
def verify_code():
    phone = request.form.get("phone", "")
    code = request.form.get("code", "").strip()
    
    if not phone or not code:
        flash("Ma'lumotlar to'liq emas.", "error")
        return redirect(url_for("index"))

    # Verify the code using db method (handles balance rewards inside)
    res = db.verify_web_code(phone, code)
    
    if res["success"]:
        user_id = res["user_id"]
        vote_reward = db.get_setting("vote_reward", str(config.VOTE_REWARD))
        
        # Notify user via telegram
        if user_id:
            send_telegram_message(
                user_id,
                f"🎉 **Tabriklaymiz!**\n"
                f"Veb-saytdagi ovozingiz muvaffaqiyatli tasdiqlandi.\n"
                f"Balansingizga **{vote_reward} so'm** qo'shildi!"
            )
            
            # Send message to referrer if exists
            user_info = db.get_user(user_id)
            if user_info and user_info['referred_by']:
                referrer_id = user_info['referred_by']
                ref_reward = db.get_setting("referral_reward", str(config.REFERRAL_REWARD))
                send_telegram_message(
                    referrer_id,
                    f"👥 Siz taklif qilgan {user_info['first_name']} sayt orqali ovoz berdi.\n"
                    f"Sizga **{ref_reward} so'm** referal bonus berildi!"
                )
        
        # Notify admin
        notify_admins(
            f"✅ **Saytdagi ovoz tasdiqlandi!**\n"
            f"📱 Telefon: `{phone}`\n"
            f"👤 Telegram ID: `{user_id if user_id else 'Ulanmagan'}`"
        )
        
        return render_template("success.html", phone=phone, vote_reward=vote_reward)
    else:
        flash("Tasdiqlash kodi xato! Iltimos, qaytadan tekshirib kiriting.", "error")
        return redirect(url_for("verify", phone=phone))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
