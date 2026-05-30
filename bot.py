import os
import re
import sqlite3
import logging
from difflib import SequenceMatcher

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("media-cms")

# ================= DB =================

db = sqlite3.connect("cms.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS sources (name TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS targets (name TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS mapping (source TEXT, target TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS blacklist (word TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS memory (text TEXT)")
db.commit()

# ================= SECURITY =================

def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# ================= CLEANING =================

def clean(text: str):
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    return text.strip()

# ================= REWRITE =================

def rewrite(text: str):
    rules = {
        "فوری": "خبر فوری",
        "اختصاصی": "گزارش اختصاصی",
        "تکمیلی": "به‌روزرسانی",
    }
    for k, v in rules.items():
        text = text.replace(k, v)
    return text

# ================= DUPLICATE =================

def is_duplicate(text: str):
    rows = cur.execute("SELECT text FROM memory ORDER BY ROWID DESC LIMIT 50").fetchall()

    for (old,) in rows:
        if SequenceMatcher(None, text, old).ratio() > 0.88:
            return True
    return False

def save_memory(text: str):
    cur.execute("INSERT INTO memory VALUES (?)", (text,))
    db.commit()

# ================= ROUTING =================

def get_targets(source):
    rows = cur.execute("SELECT target FROM mapping WHERE source=?", (source,)).fetchall()
    return [r[0] for r in rows]

# ================= PANEL UI =================

def panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Source", callback_data="add_source")],
        [InlineKeyboardButton("🎯 Target", callback_data="add_target")],
        [InlineKeyboardButton("🔗 Bind", callback_data="bind")],
        [InlineKeyboardButton("📊 Map", callback_data="map")],
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text("Media CMS Panel", reply_markup=panel())

# ================= CALLBACK =================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_owner(update):
        return

    if q.data == "map":
        rows = cur.execute("SELECT * FROM mapping").fetchall()
        text = "\n".join([f"{s} → {t}" for s, t in rows]) or "empty"
        await q.edit_message_text(text, reply_markup=panel())

    else:
        context.user_data["mode"] = q.data
        await q.edit_message_text(f"Send data for: {q.data}")

# ================= INPUT =================

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    mode = context.user_data.get("mode")
    msg = update.message.text.strip()

    if mode == "add_source":
        cur.execute("INSERT OR IGNORE INTO sources VALUES (?)", (msg,))
        db.commit()
        await update.message.reply_text("Source added")

    elif mode == "add_target":
        cur.execute("INSERT OR IGNORE INTO targets VALUES (?)", (msg,))
        db.commit()
        await update.message.reply_text("Target added")

    elif mode == "bind":
        s, t = msg.split(",")
        cur.execute("INSERT INTO mapping VALUES (?,?)", (s.strip(), t.strip()))
        db.commit()
        await update.message.reply_text("Bound")

    context.user_data["mode"] = None

# ================= CORE PIPELINE =================

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not msg.text:
        return

    source = chat.username or str(chat.id)
    text = msg.text

    # clean
    text = clean(text)

    if not text:
        return

    # rewrite
    text = rewrite(text)

    # duplicate filter
    if is_duplicate(text):
        return

    save_memory(text)

    # routing
    targets = get_targets(source)

    for t in targets:
        try:
            await context.bot.send_message(chat_id=t, text=text)
        except Exception as e:
            logger.error(e)

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    app.add_handler(MessageHandler(filters.TEXT, forward))

    print("CMS Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
