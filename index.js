const db = require('./db');
const app = require('./app');
const bot = require('./bot');

const PORT = process.env.PORT || 5000;

async function start() {
  try {
    // 1. Initialize SQLite connection and schema
    console.log("Ma'lumotlar bazasi ishga tushmoqda...");
    await db.init();

    // 2. Start Express Web Server
    console.log(`Express veb-sayti ishga tushmoqda: http://127.0.0.1:${PORT}`);
    const server = app.listen(PORT, '0.0.0.0', () => {
      console.log(`Web-sayt muvaffaqiyatli ishlamoqda: http://0.0.0.0:${PORT}`);
    });

    // 3. Start Telegram Bot Polling
    console.log("Telegram bot ishga tushmoqda...");
    bot.launch();
    console.log("Telegram bot muvaffaqiyatli polling qilmoqda.");

    console.log("\n===========================================================");
    console.log("Open Budget Simulator Node.js loyihasi ishga tushdi!");
    console.log(`Web-sayt: http://127.0.0.1:${PORT}`);
    console.log("Telegram bot orqali test qiling.");
    console.log("To'xtatish uchun Ctrl+C bosing.");
    console.log("===========================================================\n");

    // Enable graceful stop
    process.once('SIGINT', () => {
      console.log("\nLoyiha to'xtatilmoqda (SIGINT)...");
      bot.stop('SIGINT');
      server.close(() => {
        console.log("Web server yopildi.");
        process.exit(0);
      });
    });
    
    process.once('SIGTERM', () => {
      console.log("\nLoyiha to'xtatilmoqda (SIGTERM)...");
      bot.stop('SIGTERM');
      server.close(() => {
        console.log("Web server yopildi.");
        process.exit(0);
      });
    });

  } catch (err) {
    console.error(`Loyihani ishga tushirishda xatolik: ${err.message}`);
    process.exit(1);
  }
}

start();
