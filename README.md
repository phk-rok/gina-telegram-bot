# Gina Telegram Tutor (v2, dynamic topics) — Render-ready

Run Gina's 8-step English lesson in Telegram with topic-aware examples.

## Local
```
pip install -r requirements.txt
cp .env.example .env   # set BOT_TOKEN=...
python gina_telegram_bot.py
```

## Render
- Web Service → Start command: `python gina_telegram_bot.py`
- Env var: BOT_TOKEN
- Health: GET /
