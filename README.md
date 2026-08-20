# Open Budget Simulator (Test Tizimi)

Ushbu loyiha **Open Budget** (Tashabbusli Budjet) tizimiga o'xshash ovoz berish veb-sayti va Telegram bot integratsiyasining kichik test (simulyator) modelidir. 

Loyiha yordamida veb-sayt orqali ovoz berilganda qanday qilib Telegram bot bilan ma'lumot almashilishi va foydalanuvchilar qanday rag'batlantirilishini tushunib olishingiz mumkin.

## Loyiha Qanday Ishlaydi?

1. **Veb-sayt orqali ovoz berish (http://127.0.0.1:5000):**
   - Saytga telefon raqam kiritiladi.
   - Tizim 6 xonali tasdiqlash kodini yaratib, ma'lumotlar bazasiga yozadi.
   - **Simulyatsiya:** Agar ushbu telefon raqam botda ro'yxatdan o'tgan biror foydalanuvchiga tegishli bo'lsa, bot kodni to'g'ridan-to'g'ri foydalanuvchining o'ziga yuboradi. Aks holda (foydalanuvchi hali botda bo'lmasa), kod bot admin chatiga yuboriladi.
   - Saytga kod to'g'ri kiritilganda ovoz qabul qilinadi, bot foydalanuvchini va uning taklif qilgan do'stini (referal) pul mukofotlari bilan taqdirlaydi.
   
2. **Telegram Bot orqali ovoz berish:**
   - Bot ichidan turib ham telefon raqami va SMS kod kiritib ovoz berish mumkin. Adminlar kutilayotgan ovozlarni bot orqali tasdiqlashlari yoki rad etishlari mumkin.

---

## O'rnatish va Ishga Tushirish

### 1. Talablar
Kompyuteringizda **Python 3.10** yoki undan yuqori versiya o'rnatilgan bo'lishi lozim.

### 2. Kerakli kutubxonalarni o'rnatish
Loyiha papkasida terminalni ochib, quyidagi buyruqni bering:
```bash
pip install -r requirements.txt
```

### 3. Sozlash (config.py)
`config.py` faylini oching. Siz yuborgan bot tokeni avtomatik tarzda joylandi.
- `BOT_TOKEN = "8345110498:AAFqE3zgyV_s5P5mqFz_SfWkgeFDdIV2M8A"`
- `ADMINS = []` ro'yxati bo'sh qoldirildi. 
  > **Eslatma (Test rejimi):** Botga birinchi bo'lib kirib `/start` bosgan foydalanuvchi avtomatik ravishda **ADMIN** bo'ladi va admin huquqlariga ega bo'ladi.

### 4. Loyihani ishga tushirish
Veb-sayt va Telegram botni bir vaqtda parallel ishga tushirish uchun quyidagi buyruqni bering:
```bash
python run.py
```

Ishga tushgandan so'ng brauzeringizda **`http://127.0.0.1:5000`** havolasini oching.

---

## Loyiha Tuzilishi

*   `run.py` — veb-sayt va botni parallel boshqaruvchi asosiy skript.
*   `app.py` — Flask veb-ilova kodi (veb-sahifalar logikasi).
*   `bot.py` — Telegram bot kodi.
*   `database.py` — SQLite ma'lumotlar bazasi boshqaruvi.
*   `config.py` — sozlamalar.
*   `templates/` — veb-sahifa shablonlari.
