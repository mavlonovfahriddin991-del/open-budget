import threading
import time
import sys
from app import app
from bot import bot

import os

def start_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"Flask veb-sayti ishga tushmoqda: http://0.0.0.0:{port}")
    # debug=False is required when running in a thread to avoid the reloader spawning double processes
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def start_bot():
    print("Telegram bot ishga tushmoqda...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Botda xatolik yuz berdi: {e}")

if __name__ == "__main__":
    # Create threads
    t_flask = threading.Thread(target=start_flask)
    t_bot = threading.Thread(target=start_bot)
    
    # Set daemon threads so they terminate when the main program exits
    t_flask.daemon = True
    t_bot.daemon = True
    
    # Start threads
    t_flask.start()
    t_bot.start()
    
    print("\n===========================================================")
    print("Open Budget Simulator test loyihasi ishga tushdi!")
    print("Web-sayt: http://127.0.0.1:5000")
    print("Telegram bot orqali ishni boshlang.")
    print("To'xtatish uchun Ctrl+C bosing.")
    print("===========================================================\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nLoyiha to'xtatilmoqda...")
        sys.exit(0)
