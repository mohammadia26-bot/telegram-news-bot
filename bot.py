import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")

SOURCE_CHANNELS = os.getenv("SOURCE_CHANNELS", "").split(",")

SIGNATURE = "\n\n🆔 @your_channel"

logging.basicConfig(level=logging.INFO)

# ================= CLEAN =================

def clean_text(text: str):
    return text

def format_post(text: str, source: str):
    return f"{text}\n\n🟣 منبع: {source}{SIGNATURE}"

# ================= HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not msg.text:
        return

    text = clean_text(msg.text)

    source = chat.title or "Unknown"

    final_text = format_post(text, source)

    await context.bot.send_message(
        chat_id=TARGET_CHANNEL,
        text=final_text
    )

# ================= START =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.ALL & filters.Chat(SOURCE_CHANNELS), handler)
    )

    print("Bot started...")

    app.run_polling()

if __name__ == "__main__":
    main()
