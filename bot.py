import json
import os

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

load_dotenv()


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

API_AUTH = "http://127.0.0.1:8000/api/visitor/telegram-auth/"
API_PERFORMANCES = "http://127.0.0.1:8000/api/theatre/performances/"
API_RESERVATIONS = "http://127.0.0.1:8000/api/theatre/reservations/"

TOKENS_FILE = "user_tokens.json"

# ---------- Token Management ----------
def load_tokens():
    try:
        with open(TOKENS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as file:
        json.dump(tokens, file)

# ---------- Bot Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Введи свою email-адресу для авторизації.")

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()  # strip — на випадок зайвих пробілів
    telegram_id = update.effective_user.id

    response = requests.post(API_AUTH, json={"email": email, "telegram_id": telegram_id})

    if response.status_code == 200:
        access_token = response.json().get("access")

        tokens = load_tokens()
        tokens[str(telegram_id)] = access_token
        save_tokens(tokens)

        await update.message.reply_text(
            "✅ Авторизація успішна! Доступні команди:\n/performances — список вистав\n/reservations — твої бронювання"
        )
    elif response.status_code == 400:
        try:
            error_data = response.json()
            # Витягуємо повідомлення, якщо воно є
            error_msg = "; ".join(
                [f"{key}: {', '.join(val) if isinstance(val, list) else val}" for key, val in error_data.items()]
            )
        except Exception:
            error_msg = "Невідома помилка валідації (400)."

        await update.message.reply_text(f"❌ Помилка авторизації:\n{error_msg}")
    else:
        await update.message.reply_text(f"❌ Сталася помилка: {response.status_code}")

async def performances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    tokens = load_tokens()

    if telegram_id not in tokens:
        await update.message.reply_text("⚠️ Спочатку авторизуйся, надіславши свій email.")
        return

    headers = {"Authorization": f"Bearer {tokens[telegram_id]}"}
    response = requests.get(API_PERFORMANCES, headers=headers)

    if response.status_code == 200:
        performances = response.json().get("results", [])
        if performances:
            text = "🎭 Доступні вистави:\n\n"
            for perf in performances:
                show_time = perf.get("show_time")
                genre = perf.get("play_genre_name")
                title = perf.get("play_title")
                available = perf.get("tickets_available")

                text += (
                    f"🕒 {show_time}\n"
                    f"🎭 Жанр: {genre}\n"
                    f"📖 Назва: {title}\n"
                    f"🎟 Вільних квитків: {available}\n\n"
                )
        else:
            text = "Поки що немає вистав."
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("❌ Помилка при отриманні вистав.")


async def reservations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    tokens = load_tokens()

    if telegram_id not in tokens:
        await update.message.reply_text("⚠️ Спочатку авторизуйся, надіславши свій email.")
        return

    headers = {"Authorization": f"Bearer {tokens[telegram_id]}"}
    response = requests.get(API_RESERVATIONS, headers=headers)

    if response.status_code == 200:
        reservations = response.json()["results"]
        if reservations:
            text = "📋 Твої бронювання:\n\n"
            for res in reservations:
                text += f"#{res['id']} — {res['created_at'][:10]}, квитків: {len(res['tickets'])}\n"
        else:
            text = "У тебе ще немає бронювань."
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("❌ Помилка при отриманні бронювань.")

# ---------- Run Bot ----------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("performances", performances))
    app.add_handler(CommandHandler("reservations", reservations))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email))

    app.run_polling()

