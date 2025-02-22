import os
from telegram.ext import Application, CommandHandler
from bot.handlers import register_handlers, start_user_scheduler
import logging

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

def run_bot():
    logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,  # Change to DEBUG for more details
    handlers=[
        logging.FileHandler("logs/bot.log"),  # Save logs to bot.log
        logging.StreamHandler()  # Print logs to console
    ]
    )
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    register_handlers(app)
    start_user_scheduler()

    logging.info("🚀 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
