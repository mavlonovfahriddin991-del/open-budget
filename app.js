const express = require('express');
const session = require('express-session');
const flash = require('connect-flash');
const path = require('path');
const config = require('./config');
const db = require('./db');
const bot = require('./bot'); // Import our bot to send alerts natively!

const app = express();

// Configure views and rendering engine
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

// Middlewares
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: 'open_budget_mock_node_secret_key_12345',
  resave: false,
  saveUninitialized: true
}));
app.use(flash());

// Helper function to send Telegram messages
const sendTelegramMessage = async (chatId, text, extra = {}) => {
  try {
    await bot.telegram.sendMessage(chatId, text, { parse_mode: 'Markdown', ...extra });
  } catch (err) {
    console.error(`Telegram Alert Error for Chat ID ${chatId}: ${err.message}`);
  }
};

// Helper function to notify all admins
const notifyAdmins = async (text) => {
  const admins = await db.getAdmins();
  for (const adminId of admins) {
    await sendTelegramMessage(adminId, text);
  }
};

// Routes

app.get('/', async (req, res) => {
  const projectUrl = await db.getSetting("project_url", config.DEFAULT_PROJECT_URL);
  const voteReward = await db.getSetting("vote_reward", String(config.VOTE_REWARD));
  const topVoters = await db.getTopVoters(10);
  const topReferrers = await db.getTopReferrers(10);

  res.render('index', {
    project_url: projectUrl,
    vote_reward: voteReward,
    top_voters: topVoters,
    top_referrers: topReferrers,
    error: req.flash('error'),
    info: req.flash('info'),
    success: req.flash('success')
  });
});

app.post('/vote', async (req, res) => {
  let phone = (req.body.phone || '').trim();

  // Clean phone number format
  phone = phone.replace(/\s+/g, '').replace(/-/g, '');
  if (!phone.startsWith('+')) {
    if (phone.startsWith('998')) {
      phone = '+' + phone;
    } else if (phone.length === 9 && /^\d+$/.test(phone)) {
      phone = '+998' + phone;
    } else {
      req.flash('error', 'Telefon raqami noto\'g\'ri shaklda. Masalan: +998901234567');
      return res.redirect('/');
    }
  }

  if (!(phone.startsWith('+998') && phone.length === 13 && /^\d+$/.test(phone.substring(1)))) {
    req.flash('error', 'Faqat O\'zbekiston telefon raqamlari qabul qilinadi (+998XXXXXXXXX).');
    return res.redirect('/');
  }

  // Check if voted successfully already
  if (await db.checkPhoneVotedAlready(phone)) {
    req.flash('error', 'Ushbu telefon raqam orqali avvalroq ovoz berilgan!');
    return res.redirect('/');
  }

  // Generate 6-digit verification code
  const smsCode = String(Math.floor(100000 + Math.random() * 900000));

  // Check if phone number is registered in the bot
  const user = await db.getUserByPhone(phone);
  const userId = user ? user.user_id : null;

  // Add web vote
  await db.addWebVote(phone, smsCode, userId);

  // Send verification code notification
  if (userId) {
    const msgToUser = 
      `🗳️ **Open Budget Veb-sayti**\n\n` +
      `Siz sayt orqali ovoz berishni boshladingiz.\n` +
      `Tasdiqlash kodingiz: \`${smsCode}\`\n\n` +
      `Ushbu kodni veb-saytdagi oynaga kiriting.`;
    await sendTelegramMessage(userId, msgToUser);

    await notifyAdmins(
      `🌐 **Saytdan ovoz berish so'rovi!**\n` +
      `📱 Telefon: \`${phone}\`\n` +
      `👤 Foydalanuvchi: ${user.first_name} (ID: \`${userId}\`)\n` +
      `🔑 Kod foydalanuvchining Telegramiga yuborildi.`
    );
    req.flash('success', 'Tasdiqlash kodi Telegram botingizga yuborildi. Iltimos, kodni kiriting.');
  } else {
    // Non-linked number. Code goes to admins for testing
    await notifyAdmins(
      `🌐 **Saytdan ovoz berish so'rovi (Botda ulanmagan raqam)!**\n` +
      `📱 Telefon: \`${phone}\`\n` +
      `🔑 Tasdiqlash (SMS) kod: \`${smsCode}\`\n\n` +
      `⚠️ Ushbu raqam botimizdan ro'yxatdan o'tmagan. Test uchun kodni ushbu yerdan olib saytga kiritishingiz mumkin.`
    );
    req.flash('info', 'Tasdiqlash kodi yuborildi! (Loyiha test rejimida bo\'lgani uchun, agar raqamingiz botga ulanmagan bo\'lsa, kod bot adminlariga yuboriladi)');
  }

  res.redirect(`/verify?phone=${encodeURIComponent(phone)}`);
});

app.get('/verify', (req, res) => {
  const phone = req.query.phone || '';
  if (!phone) return res.redirect('/');

  res.render('verify', {
    phone: phone,
    error: req.flash('error'),
    success: req.flash('success'),
    info: req.flash('info')
  });
});

app.post('/verify_code', async (req, res) => {
  const phone = req.body.phone || '';
  const code = (req.body.code || '').trim();

  if (!phone || !code) {
    req.flash('error', 'Ma\'lumotlar to\'liq emas.');
    return res.redirect('/');
  }

  // Verify the code
  const result = await db.verifyWebCode(phone, code);

  if (result.success) {
    const userId = result.user_id;
    const voteReward = await db.getSetting("vote_reward", String(config.VOTE_REWARD));

    if (userId) {
      await sendTelegramMessage(
        userId,
        `🎉 **Tabriklaymiz!**\n` +
        `Veb-saytdagi ovozingiz muvaffaqiyatli tasdiqlandi.\n` +
        `Balansingizga **${voteReward} so'm** qo'shildi!`
      );

      const userInfo = await db.getUser(userId);
      if (userInfo && userInfo.referred_by) {
        const referrerId = userInfo.referred_by;
        const refReward = await db.getSetting("referral_reward", String(config.REFERRAL_REWARD));
        await sendTelegramMessage(
          referrerId,
          `👥 Siz taklif qilgan ${userInfo.first_name} sayt orqali ovoz berdi.\n` +
          `Sizga **${refReward} so'm** referal bonus berildi!`
        );
      }
    }

    await notifyAdmins(
      `✅ **Saytdagi ovoz tasdiqlandi!**\n` +
      `📱 Telefon: \`${phone}\`\n` +
      `👤 Telegram ID: \`${userId ? userId : 'Ulanmagan'}\``
    );

    res.render('success', { phone, vote_reward: voteReward });
  } else {
    req.flash('error', 'Tasdiqlash kodi xato! Iltimos, qaytadan tekshirib kiriting.');
    res.redirect(`/verify?phone=${encodeURIComponent(phone)}`);
  }
});

module.exports = app;
