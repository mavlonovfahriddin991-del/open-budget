# Open Budget Simulator (Node.js version)

Ushbu loyiha **Open Budget** (Tashabbusli Budjet) tizimining Node.js (Express + Telegraf.js + SQLite) da yozilgan test (simulyator) modelidir. 

Loyiha yordamida veb-sayt orqali ovoz berilganda qanday qilib Telegram bot bilan ma'lumot almashilishi va foydalanuvchilar qanday taqdirlanishini tushunib olishingiz mumkin.

## Xususiyatlari
- **Veb-sayt (Express + EJS):** Telefon raqam kiritib ovoz berish va SMS verification simulyatsiyasi.
- **Liderlar jadvali (Leaderboard):** Eng ko'p ovoz berganlar va eng ko'p do'st taklif qilganlar reytingi saytda hamda botda real vaqtda ko'rinadi.
- **Telegram Bot (Telegraf.js):** Foydalanuvchining hisobi, referal ssilkalar va balans boshqaruvi.
- **Admin paneli:** Ovozlar va yechish so'rovlarini bot orqali tasdiqlash / rad etish.

---

## O'rnatish va Ishga Tushirish

### 1. Talablar
Kompyuteringizda **Node.js (v18+)** o'rnatilgan bo'lishi lozim.

### 2. Kutubxonalarni o'rnatish
Loyiha papkasida terminalni ochib, quyidagi buyruqni bering:
```bash
npm install
```

### 3. Sozlash (config.js)
`config.js` faylini oching. Siz yuborgan bot tokeni avtomatik ulandi.
- `BOT_TOKEN = "8345110498:AAFqE3zgyV_s5P5mqFz_SfWkgeFDdIV2M8A"`
- `ADMINS = []`
  > **Eslatma (Test rejimi):** Botga birinchi bo'lib kirib `/start` bosgan foydalanuvchi avtomatik ravishda **Admin** bo'ladi.

### 4. Loyihani ishga tushirish
Veb-sayt va Telegram botni birgalikda ishga tushirish uchun quyidagi buyruqni bering:
```bash
npm start
```

Ishga tushgandan so'ng brauzeringizda **`http://127.0.0.1:5000`** havolasini oching.

---

## Loyiha Tuzilishi

*   `index.js` — sayt va botni parallel ishga tushiruvchi markaziy fayl.
*   `app.js` — Express.js veb-sayt yo'nalishlari (routes).
*   `bot.js` — Telegraf.js yordamida yozilgan bot handlerlari.
*   `database.js` — SQLite ma'lumotlar bazasi boshqaruvi.
*   `config.js` — sozlamalar.
*   `views/` — veb-sahifa shablonlari (.ejs formatida).
