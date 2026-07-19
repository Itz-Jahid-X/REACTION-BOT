import random
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8295122326:AAGax9_QzpU_j97vq6r8A173QyDABQaaixw"

REACTIONS = ["👍", "❤️", "🔥", "🥰", "👏", "💯", "⚡"]

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message is None:
            return

        emoji = random.choice(REACTIONS)

        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.id,
            reaction=[ReactionTypeEmoji(emoji)]
        )

        print("Reacted:", emoji)

    except Exception as e:
        print("Error:", e)


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, auto_react))

print("Ultra Fast Reaction Bot Started Successfully")

app.run_polling(drop_pending_updates=True)