import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")

APP_URL = os.getenv("APP_URL")  # Railway domain

logging.basicConfig(level=logging.INFO)

# ================= APP =================

app_flask = Flask(__name__)

application = Application.builder().token(BOT_TOKEN).build()

# ================= SECURITY =================

def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text("Webhook bot is running 🚀")

# ================= MESSAGE HANDLER =================

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg or not msg.text:
        return

    await context.bot.send_message(
        chat_id=TARGET_CHANNEL,
        text=f"🟢 {msg.text}"
    )

# ================= REGISTER HANDLERS =================

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, echo))

# ================= WEBHOOK ENDPOINT =================

@app_flask.post("/webhook")
async def webhook():
    data = request.get_json(force=True)

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

    return "ok"

# ================= SET WEBHOOK =================

@app_flask.get("/setwebhook")
def set_webhook():
    url = f"{APP_URL}/webhook"

    application.bot.set_webhook(url=url)

    return f"Webhook set to {url}"

# ================= MAIN =================

if __name__ == "__main__":
    print("Webhook bot running...")

    app_flask.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
