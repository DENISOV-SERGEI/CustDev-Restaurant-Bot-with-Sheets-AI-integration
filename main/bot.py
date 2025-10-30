import os
import random
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# === Загрузка переменных окружения ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_URL = os.getenv("SHEET_URL")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT")

# === Настройки Google Sheets ===
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

# === Генерация промокода (4 цифры) ===
PROMO_FILE = "daily_promo.txt"

def get_daily_promocode():
    """Создаёт или возвращает промокод (4 цифры), действующий с 12:00 до 03:00."""
    now = datetime.now()
    today_noon = datetime.combine(now.date(), time(12, 0))

    if now < today_noon:
        cycle_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        cycle_date = now.strftime("%Y-%m-%d")

    if os.path.exists(PROMO_FILE):
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            saved_date, saved_code = f.read().strip().split("|")
            if saved_date == cycle_date:
                return saved_code

    code = str(random.randint(1000, 9999))
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        f.write(f"{cycle_date}|{code}")
    return code


# === Варианты ответов ===
ANSWER_MAP = {
    1: ["Сегодня", "На этой неделе", "В этом месяце", "Ранее"],
    2: ["Бизнес-ланч", "Ужин с друзьями", "Романтический вечер", "Семейный праздник", "Другое"]
}

# === Вопросы ===
QUESTIONS = [
    "Как мы можем к Вам обращаться?",
    "Когда Вы последний раз посещали наш ресторан?\n1. Сегодня\n2. На этой неделе\n3. В этом месяце\n4. Ранее",
    "Что стало главной причиной Вашего визита?\n1. Бизнес-ланч\n2. Ужин с друзьями\n3. Романтический вечер\n4. Семейный праздник\n5. Другое",
    "Какое блюдо или напиток произвели на Вас наибольшее впечатление?",
    "Опишите атмосферу нашего заведения одним предложением.",
    "Что в обслуживании могло бы быть идеальным для Вас?",
    "Спасибо за честность! Последний вопрос: Если бы Вы могли изменить одну вещь в нашем ресторане, что бы это было?"
]


# === Основная логика ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и начало опроса — сразу для всех случаев."""
    context.user_data.clear()
    context.user_data["step"] = 0
    chat = update.effective_chat

    # Если пользователь пришёл по ссылке с параметром
    if context.args and context.args[0] == "interview":
        welcome_text = (
            'Приветствуем в ресторане "La Bella"! 🍝\n'
            'Спасибо, что согласились пройти короткое интервью — всего 7 вопросов!\n'
            'За участие — приятный бонус 🎁\n\n'
        )
    else:
        welcome_text = (
            'Приветствуем в ресторане "La Bella"! 🍝\n'
            'Помогите нам стать лучше — пройдите короткое интервью, всего 7 вопросов.\n'
            'За участие — приятный бонус 🎁\n\n'
        )

    # Сразу начинаем опрос
    await chat.send_message(welcome_text + QUESTIONS[0])


def convert_answer(step: int, user_input: str) -> str:
    """Если пользователь вводит цифру — возвращает текстовый ответ."""
    try:
        number = int(user_input.strip())
        if step == 1 and 1 <= number <= len(ANSWER_MAP[1]):
            return ANSWER_MAP[1][number - 1]
        elif step == 2 and 1 <= number <= len(ANSWER_MAP[2]):
            return ANSWER_MAP[2][number - 1]
    except ValueError:
        pass
    return user_input.strip()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step", 0)
    text = update.message.text.strip()

    # === Шаг 0: имя пользователя ===
    if step == 0:
        context.user_data["Имя"] = text
        context.user_data["UserID"] = update.message.from_user.id
        context.user_data["Username"] = (
            f"@{update.message.from_user.username}" if update.message.from_user.username else "—"
        )
        context.user_data["step"] = 1
        await update.message.reply_text(f"Приятно познакомиться, {text}! {QUESTIONS[1]}")
        return

    # === Список полей таблицы (соответствует структуре) ===
    fields = [
        "Последний визит",
        "Причина визита",
        "Впечатление от блюда",
        "Оценка атмосферы",
        "Ожидания от сервиса",
        "Предложение по улучшению"
    ]

    if 1 <= step <= 6:
        answer = convert_answer(step, text)
        context.user_data[fields[step - 1]] = answer
        context.user_data["step"] += 1

    # === Следующий вопрос ===
    if context.user_data["step"] < len(QUESTIONS):
        next_q = QUESTIONS[context.user_data["step"]]
        await update.message.reply_text(next_q)
    else:
        # === Все ответы получены, записываем в Google Sheets ===
        promo = get_daily_promocode()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            context.user_data.get("Username"),   # ID / Username
            timestamp,                           # Дата опроса
            promo,                               # Промо код
            context.user_data.get("Имя"),        # Имя
            context.user_data.get("Последний визит"),
            context.user_data.get("Причина визита"),
            context.user_data.get("Впечатление от блюда"),
            context.user_data.get("Оценка атмосферы"),
            context.user_data.get("Ожидания от сервиса"),
            context.user_data.get("Предложение по улучшению"),
            "", "", "", ""  # Сегмент | Тональность | Гипотеза (меню) | Гипотеза (обслуживание)
        ]

        sheet.append_row(row)
        await update.message.reply_text(
            f"💚 Спасибо за участие!\n"
            f"Ваш промокод на скидку 5%: {promo} — действует до 03:00 следующего дня.\n"
            "Ждём Вас снова в La Bella! 🌿"
        )
        context.user_data.clear()


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Давайте продолжим наш опрос 😊")


# === Запуск бота ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.run_polling()


if __name__ == "__main__":
    main()
