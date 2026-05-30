import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")

SIGNATURE = "\n\n🆔 @your_channel"

logging.basicConfig(level=logging.INFO)

# ================= DB =================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sources (
    username TEXT PRIMARY KEY
)
""")
conn.commit()

def add_source_db(username):
    cursor.execute("INSERT OR IGNORE INTO sources VALUES (?)", (username,))
    conn.commit()

def remove_source_db(username):
    cursor.execute("DELETE FROM sources WHERE username=?", (username,))
    conn.commit()

def get_sources():
    cursor.execute("SELECT username FROM sources")
    return [row[0] for row in cursor.fetchall()]

# ================= SECURITY =================

def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# ================= FORMAT =================

def format_post(text, source):
    return f"{text}\n\n🟣 منبع: {source}{SIGNATURE}"

def clean(text):
    return text

# ================= PANEL =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text(
        "/addsource username\n"
        "/removesource username\n"
        "/listsources"
    )

async def addsource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    if not context.args:
        return await update.message.reply_text("مثال: /addsource bbc_persian")

    add_source_db(context.args[0])
    await update.message.reply_text("اضافه شد")

async def removesource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    if not context.args:
        return await update.message.reply_text("مثال: /removesource bbc_persian")

    remove_source_db(context.args[0])
    await update.message.reply_text("حذف شد")

async def listsources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    sources = get_sources()
    await update.message.reply_text("\n".join(sources) if sources else "خالی است")

# ================= MESSAGE HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not msg.text:
        return

    sources = get_sources()

    if chat.username not in sources:
        return

    source = chat.title or chat.username
    text = clean(msg.text)

    final = format_post(text, source)

    await context.bot.send_message(
        chat_id=TARGET_CHANNEL,
        text=final
    )

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addsource", addsource))
    app.add_handler(CommandHandler("removesource", removesource))
    app.add_handler(CommandHandler("listsources", listsources))

    app.add_handler(MessageHandler(filters.ALL, handler))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
