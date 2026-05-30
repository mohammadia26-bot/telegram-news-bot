import os
import sqlite3
import logging
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

# ================= DB =================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS sources (name TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS targets (name TEXT PRIMARY KEY)")
cur.execute("""
CREATE TABLE IF NOT EXISTS mapping (
    source TEXT,
    target TEXT
)
""")
conn.commit()

# ================= SECURITY =================

def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# ================= DB HELPERS =================

def add_source(name):
    cur.execute("INSERT OR IGNORE INTO sources VALUES (?)", (name,))
    conn.commit()

def add_target(name):
    cur.execute("INSERT OR IGNORE INTO targets VALUES (?)", (name,))
    conn.commit()

def bind(source, target):
    cur.execute("INSERT INTO mapping VALUES (?, ?)", (source, target))
    conn.commit()

def unbind(source, target):
    cur.execute("DELETE FROM mapping WHERE source=? AND target=?", (source, target))
    conn.commit()

def get_sources():
    return [r[0] for r in cur.execute("SELECT name FROM sources")]

def get_targets():
    return [r[0] for r in cur.execute("SELECT name FROM targets")]

def get_map():
    return cur.execute("SELECT source, target FROM mapping").fetchall()

# ================= PANEL UI =================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Source", callback_data="add_source")],
        [InlineKeyboardButton("🎯 Add Target", callback_data="add_target")],
        [InlineKeyboardButton("🔗 Bind", callback_data="bind")],
        [InlineKeyboardButton("❌ Unbind", callback_data="unbind")],
        [InlineKeyboardButton("📋 Show Map", callback_data="show_map")]
    ])

# ================= COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text(
        "📊 Mapping Panel",
        reply_markup=main_menu()
    )

# ================= CALLBACK HANDLER =================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_owner(update):
        return

    data = q.data

    if data == "show_map":
        m = get_map()
        text = "\n".join([f"{s} → {t}" for s, t in m]) or "empty"
        await q.edit_message_text(text, reply_markup=main_menu())

    elif data == "add_source":
        context.user_data["mode"] = "add_source"
        await q.edit_message_text("Send source channel username")

    elif data == "add_target":
        context.user_data["mode"] = "add_target"
        await q.edit_message_text("Send target channel username")

    elif data == "bind":
        context.user_data["mode"] = "bind"
        await q.edit_message_text("Send: source,target")

    elif data == "unbind":
        context.user_data["mode"] = "unbind"
        await q.edit_message_text("Send: source,target")

# ================= TEXT INPUT =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    mode = context.user_data.get("mode")
    text = update.message.text.strip()

    if mode == "add_source":
        add_source(text)
        await update.message.reply_text("Source added ✔")

    elif mode == "add_target":
        add_target(text)
        await update.message.reply_text("Target added ✔")

    elif mode == "bind":
        s, t = text.split(",")
        bind(s.strip(), t.strip())
        await update.message.reply_text("Bound ✔")

    elif mode == "unbind":
        s, t = text.split(",")
        unbind(s.strip(), t.strip())
        await update.message.reply_text("Unbound ✔")

    context.user_data["mode"] = None

# ================= ROUTING ENGINE =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not msg.text:
        return

    source = chat.username
    text = msg.text

    routes = get_map()

    for s, t in routes:
        if s == source:
            await context.bot.send_message(
                chat_id=t,
                text=text
            )

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL, text_handler))
    app.add_handler(MessageHandler(filters.ALL, handler))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
