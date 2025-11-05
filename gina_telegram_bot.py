
# gina_telegram_bot.py
# Render-ready: runs Telegram bot (python-telegram-bot v21) and a tiny FastAPI health server.
# Environment: BOT_TOKEN (required)
# Optional: OPENAI_API_KEY (if you want GPT calls later), CHAT_ID (for future broadcasts)

import os, asyncio, re, random
from dataclasses import dataclass
from typing import Dict, Literal, List

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------- env ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8000"))  # Render will inject PORT for Web Service
if not BOT_TOKEN:
    raise SystemExit("Missing BOT_TOKEN in environment (.env)")

# ---------- FastAPI (Render health check) ----------
app_http = FastAPI()

@app_http.get("/")
def root():
    return {"status": "ok", "service": "gina-telegram-bot"}

# ---------- Gina 8-step minimal engine ----------
TOPICS: List[str] = [
    "At a convenience store (sending a parcel)",
    "Booking a haircut at a salon",
    "Buying over-the-counter medicine at a pharmacy",
    "Returning an item at a clothing store",
    "Asking for directions in a subway station",
    "Scheduling a meeting at the office front desk",
    "Ordering takeout over the phone",
    "Checking in at a hotel late at night"
]
Step = Literal["S1","S2","S3","S4","S5","S6","S7","S8","IDLE"]

@dataclass
class Session:
    step: Step = "IDLE"
    topic: str = ""
    last_topic: str = ""
    shadow_ix: int = 0

STATE: Dict[int, Session] = {}

def pick_new_topic(last: str) -> str:
    c = [t for t in TOPICS if t != last]
    return random.choice(c) if c else random.choice(TOPICS)

def kb(*rows):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows])

def kb_yes_wait_reset():
    return kb([("✅ 네, 시작할게요","YES"),("⏳ 잠시만요","WAIT")],[("🔄 Reset","RESET")])

def step1(topic: str) -> str:
    return (
        "⭐ **STEP 1: 미션 제시**\n"
        f"오늘의 미션/역할: {topic}\n"
        "상황 시나리오: 당신은 해당 장소에서 필요한 일을 처리해야 합니다. 저는 직원/상대역(지나)입니다.\n\n"
        "핵심 표현 5가지:\n"
        "1) Could you help me with…? — …좀 도와주실 수 있나요?\n"
        "2) I’d like to… — …하려고 합니다.\n"
        "3) Is it possible to…? — …가능할까요?\n"
        "4) Could you explain how to…? — …하는 방법을 설명해 주실 수 있나요?\n"
        "5) That’s all, thank you. — 여기까지입니다. 감사합니다.\n\n"
        "전체 대화 예시:\n"
        "Teacher: \"Hello! How can I help you today?\"\n"
        "User: \"Hi, I’d like to send a small parcel, please.\"\n"
        "Teacher: \"Sure. Domestic or international?\"\n"
        "User: \"Domestic, please.\"\n"
        "Teacher: \"Great. Please fill out this form.\"\n"
        "User: \"Got it. That’s all, thank you.\"\n\n"
        "오늘의 꿀팁: 요청할 때 ‘I want…’ 대신 ‘I’d like to…’를 쓰면 더 공손하게 들립니다."
    )

def step2_demo() -> str:
    return (
        "안녕하세요! 튜터 지나입니다. 제가 먼저 **1인 2역 시연**을 보여드릴게요.\n"
        "(시연 시작)\n"
        "Gina (Staff): \"Hello! How can I help you today?\"\n"
        "Gina (Customer): \"Hi, I’d like to send a small parcel, please.\"\n"
        "Gina (Staff): \"Sure. Domestic or international?\"\n"
        "Gina (Customer): \"Domestic, please.\"\n"
        "Gina (Staff): \"Great. Please fill out this form.\"\n"
        "Gina (Customer): \"Okay. That’s all, thank you.\"\n"
        "(시연 끝)\n\n"
        "자, 이제 저와 함께 역할극을 해볼까요? 준비되셨나요?"
    )

def step3_prompt() -> str:
    return ("**(STEP 3: 기본 롤플레이)**\n"
            "Teacher: \"Good evening! What can I get for you today?\"\n"
            "_(영어로 자유 답변)_")

def step4_feedback() -> str:
    return ("롤플레이 좋았어요! 😊\n"
            "응용 롤플레이를 위해 표현 2가지를 드릴게요:\n"
            "• I have a small request: …\n"
            "• Could you double-check that for me?\n"
            "이 표현들을 사용해 응용 챌린지에 도전해 보시겠어요?")

def step5_demo_and_start() -> str:
    return ("응용 상황 시연을 보여드릴게요.\n"
            "(시연) Gina(Staff): \"Are you ready to proceed?\"\n"
            "Gina(Customer): \"Yes, I have a small request: could you double-check the address?\"\n"
            "Gina(Staff): \"Of course. It matches the form.\"\n"
            "(끝)\n\n"
            "자, 그럼 두 번째 롤플레이를 시작해볼까요?\n"
            "Teacher: \"Are you ready to proceed, or do you need a moment?\"")

def step6_summary() -> str:
    return ("훌륭해요! 오늘 ‘I’d like to…’와 정중한 요청 표현을 잘 쓰셨어요.\n"
            "교정 팁: “I want to …” 대신 “I’d like to …”가 더 공손합니다.\n"
            "추가 어휘: receipt, fragile, domestic, declare\n"
            "암기 문장: “Could you double-check that for me?”")

def step7_lines() -> List[str]:
    return [
        "What would you like to do today?",
        "I’d like to send a small parcel.",
        "Could you double-check that for me?",
        "That’s all, thank you."
    ]

def step8_finish() -> str:
    return ("오늘 수고 많으셨어요! 🎉\n"
            "새로운 시나리오에 도전하시겠어요, 아니면 여기까지 할까요?\n"
            "• 새로운 시나리오 → \"새로운 시나리오\"\n"
            "• 종료 → \"여기까지\"")

async def go_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE, s: Session):
    chat = update.effective_chat
    if s.step == "S1":
        await chat.send_message(step1(s.topic), reply_markup=kb([("▶ STEP 2로", "NEXT")],[("🔄 Reset","RESET")]), parse_mode="Markdown")
    elif s.step == "S2":
        await chat.send_message(step2_demo(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 네, 시작할게요","YES"),InlineKeyboardButton("⏳ 잠시만요","WAIT")],[ [InlineKeyboardButton("🔄 Reset","RESET")] ]]), parse_mode=None)
    elif s.step == "S3":
        await chat.send_message(step3_prompt())
    elif s.step == "S4":
        await chat.send_message(step4_feedback(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 네","YES")],[InlineKeyboardButton("🔄 Reset","RESET")]]))
    elif s.step == "S5":
        await chat.send_message(step5_demo_and_start())
    elif s.step == "S6":
        await chat.send_message(step6_summary())
    elif s.step == "S7":
        lines = step7_lines()
        if s.shadow_ix >= len(lines):
            s.step = "S8"
            await go_step(update, ctx, s); return
        await chat.send_message(
            f"쉐도잉 {s.shadow_ix+1}/{len(lines)}\n저를 따라 말해보세요:\n\"{lines[s.shadow_ix]}\"",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("다음 문장 ▶","SHADOW_NEXT")],[InlineKeyboardButton("🔄 Reset","RESET")]])
        )
    elif s.step == "S8":
        await chat.send_message(step8_finish(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("새로운 시나리오","NEW")],[InlineKeyboardButton("여기까지","END")]]))
    else:
        await chat.send_message("“시작!”이라고 입력하시면 STEP 1부터 진행할게요.")

def ensure(chat_id: int):
    if chat_id not in STATE:
        STATE[chat_id] = Session()

def next_step(s: Session):
    order = ["S1","S2","S3","S4","S5","S6","S7","S8"]
    if s.step in order:
        idx = order.index(s.step)
        s.step = order[min(idx+1, len(order)-1)]
    else:
        s.step = "S1"

# ---------- Handlers ----------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure(chat_id)
    s = STATE[chat_id]
    s.last_topic = s.topic or s.last_topic
    s.topic = pick_new_topic(s.last_topic)
    s.step, s.shadow_ix = "S1", 0
    await go_step(update, ctx, s)

async def text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure(chat_id)
    s = STATE[chat_id]
    msg = (update.message.text or "").strip()

    if msg in ("시작", "시작!", "/시작"):
        return await cmd_start(update, ctx)

    if s.step == "IDLE":
        return await update.message.reply_text("지금은 대기 상태예요. “시작!”이라고 입력하면 STEP 1부터 진행합니다.")

    if s.step == "S2":
        if re.search(r"(네|시작|좋|ok|ready|go)", msg, re.I):
            s.step = "S3"
            return await go_step(update, ctx, s)
        return await update.message.reply_text("준비되셨다면 “네” 또는 “시작”이라고 답해 주세요.")

    if s.step == "S3":
        s.step = "S4"; return await go_step(update, ctx, s)

    if s.step == "S4":
        if re.search(r"(네|좋|ok|시작)", msg, re.I):
            s.step = "S5"; return await go_step(update, ctx, s)
        return await update.message.reply_text("응용 챌린지 진행할까요? “네”라고 답해 주세요.")

    if s.step == "S5":
        s.step = "S6"; return await go_step(update, ctx, s)

    if s.step == "S6":
        s.step = "S7"; s.shadow_ix = 0; return await go_step(update, ctx, s)

    if s.step == "S7":
        return await update.message.reply_text("좋아요! 버튼으로 다음 문장으로 넘어가요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("다음 문장 ▶","SHADOW_NEXT")]]))

    if s.step == "S8":
        if "새로운" in msg:
            return await cmd_start(update, ctx)
        return await update.message.reply_text("세션을 종료할까요? “여기까지” 또는 “새로운 시나리오” 중 하나를 선택해 주세요.")

async def on_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure(chat_id)
    s = STATE[chat_id]
    data = update.callback_query.data
    await update.callback_query.answer()

    if data == "RESET":
        STATE[chat_id] = Session()
        return await update.effective_chat.send_message("세션이 초기화되었어요. “시작!”이라고 입력해 주세요.")
    if data in ("NEXT","YES"):
        next_step(s); return await go_step(update, ctx, s)
    if data == "WAIT":
        return await update.effective_chat.send_message("알겠습니다. 준비되시면 “시작”이라고 알려주세요.")
    if data == "NEW":
        return await cmd_start(update, ctx)
    if data == "END":
        STATE[chat_id] = Session()
        return await update.effective_chat.send_message("오늘 학습을 종료합니다. 수고 많으셨어요! 👋")
    if data == "SHADOW_NEXT":
        if s.step != "S7": return
        s.shadow_ix += 1
        return await go_step(update, ctx, s)

async def run_bot_and_http():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CallbackQueryHandler(on_cb))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # Run telegram polling and FastAPI server concurrently
    async def _run_polling():
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        # keep running
        await asyncio.Event().wait()

    config = uvicorn.Config(app_http, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(_run_polling(), server.serve())

if __name__ == "__main__":
    asyncio.run(run_bot_and_http())
