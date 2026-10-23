import os
import random
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    ReactionTypeEmoji,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ChatMemberHandler,
    filters,
)

# ------------------------------------------------------------------
# 1. Logging (structured)
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 2. Configuration
# ------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Can be None
REACTIONS = ["👍", "❤️", "🔥", "🥰", "👏", "💯", "⚡"]

# ------------------------------------------------------------------
# 2b. Chat registry  (used by /channel)
# ------------------------------------------------------------------
# id -> {"id", "title", "username", "type"}
known_chats: dict[int, dict] = {}

def track_chat(chat):
    """Record a channel / group the bot is in."""
    if chat is None:
        return
    if chat.type in ("group", "supergroup", "channel"):
        known_chats[chat.id] = {
            "id": chat.id,
            "title": chat.title or "(no title)",
            "username": chat.username,     # may be None for private groups
            "type": chat.type,
        }

# ------------------------------------------------------------------
# 3. Telegram Application – built later (not at import time)
# ------------------------------------------------------------------
telegram_app = None

def build_telegram_app(token: str):
    """Build the Application and attach handlers."""
    app = Application.builder().token(token).build()

    async def auto_react(update: Update, context):
        # Works for private/group messages AND channel posts.
        message = update.effective_message
        if message is None:
            return
        track_chat(message.chat)  # record every chat we hear from
        emoji = random.choice(REACTIONS)
        try:
            await context.bot.set_message_reaction(
                chat_id=message.chat_id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji)],
            )
            logger.info(f"Reacted {emoji} to message {message.message_id}")
        except Exception as e:
            logger.error(f"Reaction failed: {e}")

    async def on_my_chat_member(update: Update, context):
        cmu = update.my_chat_member
        if cmu is None:
            return
        chat = cmu.chat
        status = cmu.new_chat_member.status
        if status in ("member", "administrator", "creator"):
            track_chat(chat)
            logger.info(f"Bot added to {chat.type} {chat.id} ({chat.title})")
        elif status in ("left", "kicked"):
            removed = known_chats.pop(chat.id, None)
            if removed:
                logger.info(f"Bot removed from {chat.type} {chat.id} ({chat.title})")

    # NEW: /start — only in bot's inbox, shows "add me to channel" button
    async def start(update: Update, context):
        message = update.effective_message
        if message is None:
            return
        # Only respond in private chat — nothing anywhere else
        if message.chat.type != "private":
            return

        bot_username = context.bot.username
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add me to your channel",
                        url=f"https://t.me/{bot_username}?startchannel=true&admin=post_messages",
                    )
                ]
            ]
        )
        await message.reply_text(
            "👋 <b>Hi! I'm an auto-reaction bot.</b>\n\n"
            "Add me to your channel and I'll automatically react "
            "to every new post with a random emoji.\n\n"
            "👇 Tap the button below to add me:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    # /channel — pretty list of tracked chats (private chat only)
    async def list_channels(update: Update, context):
        message = update.effective_message
        if message is None:
            return

        if message.chat.type != "private":
            await message.reply_text("Please use /channel in a private chat with me.")
            return

        if not known_chats:
            await message.reply_text(
                "No channels/groups tracked yet.\n\n"
                "Add me to a channel/group, or send any message there — "
                "I'll record it and it will show up here."
            )
            return

        items = sorted(known_chats.values(), key=lambda x: (x["title"] or "").lower())
        n_channel = sum(1 for i in items if i["type"] == "channel")
        n_group = len(items) - n_channel

        header = (
            f"📋 <b>Channels &amp; Groups</b>  ({len(items)} total)\n"
            f"<i>{n_channel} channel(s) · {n_group} group(s)</i>"
        )
        lines = [header]
        for i, info in enumerate(items, 1):
            username = f"@{info['username']}" if info["username"] else "—"
            lines.append(
                f"\n<b>{i}. {info['title']}</b>\n"
                f"   • ID: <code>{info['id']}</code>\n"
                f"   • Username: {username}\n"
                f"   • Type: {info['type']}"
            )

        text = "\n".join(lines)

        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.reply_text(text[i:i + 4000], parse_mode="HTML")
        else:
            await message.reply_text(text, parse_mode="HTML")

    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("channel", list_channels))
    # Skip commands so the bot doesn't react to /start, /channel, etc.
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, auto_react))
    return app

# ------------------------------------------------------------------
# 4. FastAPI lifespan (startup / shutdown)
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    # ---- STARTUP ----
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set.")
        telegram_app = None
    else:
        logger.info("Building Telegram Application...")
        telegram_app = build_telegram_app(BOT_TOKEN)
        await telegram_app.initialize()
        logger.info("Telegram Application initialised.")

    yield

    # ---- SHUTDOWN ----
    if telegram_app:
        logger.info("Shutting down Telegram Application...")
        await telegram_app.shutdown()
        logger.info("Telegram Application shut down.")

app = FastAPI(lifespan=lifespan)

# ------------------------------------------------------------------
# 5. Webhook endpoint
# ------------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """Handle incoming Telegram updates."""
    global telegram_app

    if telegram_app is None:
        logger.error("Telegram app not initialised (missing BOT_TOKEN?)")
        return Response(status_code=500, content="Bot not configured")

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON: {e}")
        return Response(status_code=400, content="Invalid JSON")

    try:
        update = Update.de_json(body, telegram_app.bot)
        if update is None:
            logger.warning("Empty update received")
            return Response(status_code=200, content="OK")

        await telegram_app.process_update(update)
        return Response(status_code=200, content="OK")
    except Exception as e:
        logger.exception(f"Unhandled error processing update: {e}")
        return Response(status_code=200, content="OK")

# ------------------------------------------------------------------
# 6. Utility: set webhook
# ------------------------------------------------------------------
@app.get("/set_webhook")
async def set_webhook(request: Request):
    """Helper to set the webhook URL."""
    global telegram_app
    if telegram_app is None:
        return {"error": "Bot not configured"}

    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return {"error": "Cannot determine host"}
    scheme = request.headers.get("x-forwarded-proto", "https")
    webhook_url = f"{scheme}://{host}/webhook"

    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
        return {"status": "Webhook set", "url": webhook_url}
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return {"error": str(e)}

# ------------------------------------------------------------------
# 7. Root health check
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "Telegram bot is running", "webhook": "/webhook"}
