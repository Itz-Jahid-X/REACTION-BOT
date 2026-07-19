# 🚀 Telegram Auto Reaction Bot (Vercel)

A production-ready Telegram Auto Reaction Bot built with **FastAPI**, **python-telegram-bot**, and **Vercel Serverless Functions**.

The bot automatically reacts to every incoming message with a random emoji using Telegram Bot API.

---

# ✨ Features

- ⚡ FastAPI Webhook
- 🚀 Vercel Serverless Ready
- 🎲 Random Emoji Reactions
- 🔥 Production Ready
- 🛡 Global Error Handling
- 📄 Structured Logging
- ♻ Async Processing
- ⚙ Environment Variable Support
- 💚 Lightweight & Fast

---

# 📦 Tech Stack

- Python 3.12+
- FastAPI
- python-telegram-bot v21+
- Vercel Serverless

---

# 📁 Project Structure

```
.
├── main.py
├── requirements.txt
├── vercel.json
└── README.md
```

---

# 🔑 Environment Variable

Create an Environment Variable inside Vercel.

Name

```
BOT_TOKEN
```

Value

```
YOUR_TELEGRAM_BOT_TOKEN
```

---

# 📥 Installation

Clone the repository

```bash
git clone https://github.com/USERNAME/REPOSITORY.git
```

Go to project

```bash
cd REPOSITORY
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# ☁ Deploy on Vercel

Push your project to GitHub.

Open

```
https://vercel.com
```

Import your repository.

Add Environment Variable

```
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

Deploy the project.

---

# 🔗 Set Webhook

After deployment open:

```
https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=https://YOUR_PROJECT.vercel.app/webhook
```

Example Response

```json
{
    "ok": true,
    "result": true,
    "description": "Webhook was set"
}
```

---

# ✅ Verify Webhook

Open

```
https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo
```

Example

```json
{
    "ok": true,
    "result": {
        "url": "https://YOUR_PROJECT.vercel.app/webhook"
    }
}
```

If the URL is correct, the webhook is active.

---

# 🌐 Health Check

Visit

```
https://YOUR_PROJECT.vercel.app
```

Expected Response

```json
{
    "status": "Telegram bot is running",
    "webhook": "/webhook"
}
```

---

# 🎲 Default Emoji List

```
👍
❤️
🔥
🥰
👏
💯
⚡
```

You can edit the list inside

```python
REACTIONS = [
    "👍",
    "❤️",
    "🔥",
    "🥰",
    "👏",
    "💯",
    "⚡"
]
```

---

# 📄 requirements.txt

```
fastapi
python-telegram-bot==21.6
httpx==0.28.1
```

---

# 📄 vercel.json

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ]
}
```

---

# 🔄 Redeploy

Whenever you change:

- BOT_TOKEN
- Code
- requirements.txt

Redeploy your Vercel project.

---

# 📜 License

MIT License

---

# ❤️ Credits

Developed with Python, FastAPI and Telegram Bot API.

Powered by Vercel Serverless Functions.
