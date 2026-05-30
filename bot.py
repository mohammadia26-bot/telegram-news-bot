import re
import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# =========================
# CONFIG (Railway ENV)
# =========================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID"))

SESSION_NAME = "news_session"

TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@your_channel")

SOURCE_CHANNELS = os.getenv("SOURCE_CHANNELS", "").split(",")

SIGNATURE = "\n\n🆔 @your_channel"

# =========================
# LOGGING
# =========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# =========================
# CLEAN TEXT
# =========================

def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    return text.strip()

# =========================
# FORMAT
# =========================

def format_post(text: str, source: str) -> str:
    return f"{text}\n\n🟣 منبع: {source}{SIGNATURE}"

# =========================
# PUBLISH
# =========================

async def publish(msg, media=None):
    try:
        if media:
            await client.send_file(TARGET_CHANNEL, media, caption=msg)
        else:
            await client.send_message(TARGET_CHANNEL, msg)

    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)

# =========================
# HANDLER
# =========================

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):

    try:
        text = event.message.message
        if not text:
            return

        # فقط متن تمیز
        cleaned = clean_text(text)

        # اسم کانال بدون لینک و @
        source = event.chat.title or "نامشخص"

        final = format_post(cleaned, source)

        if event.message.media:
            media = await event.message.download_media()
            await publish(final, media)
        else:
            await publish(final)

        logger.info(f"Posted from: {source}")

    except Exception as e:
        logger.error(e)

# =========================
# MAIN
# =========================

async def main():
    logger.info("Bot started...")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
