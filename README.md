# Gina Telegram Tutor (Render-ready)

A 24/7 Telegram bot that runs Gina's **8-step English lesson** flow. Works on Render as a Web Service (kept alive via a tiny FastAPI health server) and uses polling to receive Telegram updates.

## 1) Local test

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set BOT_TOKEN=...

python gina_telegram_bot.py
```

In Telegram: open your bot link `https://t.me/<your_bot_username>` and press **Start** (or send "시작!").

## 2) Deploy on Render

1. Push this folder to a GitHub repo.
2. Go to Render → **New** → **Web Service** → connect your repo.
3. Environment: Python, Build Command (auto), Start Command:
   ```
   python gina_telegram_bot.py
   ```
4. Add Environment Variables:
   - `BOT_TOKEN` = your Telegram bot token
   - (Render will set `PORT` automatically)
5. Deploy. The service will expose `GET /` returning JSON for health.

> If Render suggests "Background Worker", you can also use that type with the same command. For Web Service, this project already listens on `$PORT`.

## 3) Optional: Daily 8AM KST Reminder (GitHub Actions)

Use your previous workflow that calls Telegram `sendMessage` via `curl` to send a reminder each morning. The bot here remains online 24/7 on Render for conversations.

## Troubleshooting

- Bot doesn't respond: ensure you pressed **Start** (send `/start`) in the bot chat.  
- 400 chat not found: wrong chat id (for broadcast) or you didn't DM the bot yet.  
- 401 unauthorized: invalid or revoked `BOT_TOKEN`.  
- Render sleeps: free tier may sleep on inactivity; a new message will wake it.

Happy learning! ☕
