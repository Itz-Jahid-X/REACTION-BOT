import os
import random
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, MessageHandler, filters

# ------------------------------------------------------------------
# 1. Configuration
# ------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Must be set in Vercel environment
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

REACTIONS = ["👍", "❤️", "🔥", "🥰", "👏", "💯", "⚡"]

# ------------------------------------------------------------------
# 2. Logging setup (structured and production-friendly)
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 3. Telegram Application (initialised once at startup)
# ------------------------------------------------------------------
telegram_app = Application.builder().token(BOT_TOKEN).build()

# 3a. Reaction handler
async def auto_react(update: Update, context):
    """React to any incoming message with a random emoji."""
    if update.message is None:
        return
    emoji = random.choice(REACTIONS)
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.id,
            reaction=[ReactionTypeEmoji(emoji)],
        )
        logger.info(f"Reacted {emoji} to message {update.message.id}")
    except Exception as e:
        logger.error(f"Reaction failed: {e}")

telegram_app.add_handler(MessageHandler(filters.ALL, auto_react))

# ------------------------------------------------------------------
# 4. FastAPI lifespan events (startup / shutdown)
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise the Telegram Application (bot, updater, etc.)
    logger.info("Starting up Telegram Application...")
    await telegram_app.initialize()
    logger.info("Telegram Application initialised.")
    yield
    # Shutdown: cleanly stop the application
    logger.info("Shutting down Telegram Application...")
    await telegram_app.shutdown()
    logger.info("Telegram Application shut down.")

app = FastAPI(lifespan=lifespan)

# ------------------------------------------------------------------
# 5. Webhook endpoint (receives Telegram updates)
# ------------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """
    Handle incoming Telegram updates via webhook.
    - Parse JSON body, build Update object.
    - Process update through the Telegram Application.
    - Always return 200 OK (Telegram expects this).
    """
    try:
        # Read raw body and parse JSON
        body = await request.json()
        logger.debug("Received webhook payload")
    except Exception as e:
        logger.error(f"Invalid JSON payload: {e}")
        return Response(status_code=400, content="Invalid JSON")

    try:
        # Build Update object
        update = Update.de_json(body, telegram_app.bot)
        if update is None:
            logger.warning("Received empty update")
            return Response(status_code=200, content="OK")  # still return 200

        # Process the update asynchronously (non-blocking)
        await telegram_app.process_update(update)
        return Response(status_code=200, content="OK")
    except Exception as e:
        # Global exception handling: log and still return 200 to avoid retries
        logger.exception(f"Unhandled error while processing update: {e}")
        return Response(status_code=200, content="OK")  # Telegram expects 2xx

# ------------------------------------------------------------------
# 6. Utility endpoint: set webhook programmatically
# ------------------------------------------------------------------
@app.get("/set_webhook")
async def set_webhook(request: Request):
    """
    Helper endpoint to set the webhook URL for this deployment.
    Determines the public URL from request headers (Vercel provides x-forwarded-*).
    Usage: visit https://your-app.vercel.app/set_webhook
    """
    # Build public URL from headers
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
# 7. Root endpoint (optional health check)
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "Telegram bot is running", "webhook": "/webhook"}