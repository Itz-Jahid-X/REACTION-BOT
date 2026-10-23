import os
import random
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, MessageHandler, filters

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

    app.add_handler(MessageHandler(filters.ALL, auto_react))
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
        # We still let the app start, but webhook calls will fail.
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

    # Check if the bot is ready
    if telegram_app is None:
        logger.error("Telegram app not initialised (missing BOT_TOKEN?)")
        return Response(status_code=500, content="Bot not configured")

    # Parse payload
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
        # Log error but always return 200 to avoid Telegram retries
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
