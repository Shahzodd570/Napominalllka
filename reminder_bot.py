import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Файл для хранения напоминаний
DATA_FILE = "reminders.json"

# Инициализация планировщика
scheduler = BackgroundScheduler()
scheduler.start()

# 📦 Загрузка напоминаний из файла
def load_reminders():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 💾 Сохранение напоминаний в файл
def save_reminders(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

reminders = load_reminders()

# 🔔 Функция отправки напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id, text):
    await context.bot.send_message(chat_id=user_id, text=f"🔔 Напоминание: {text}")
    # Удаляем напоминание после отправки
    user_id_str = str(user_id)
    if user_id_str in reminders:
        reminders[user_id_str] = [r for r in reminders[user_id_str] if r["text"] != text]
        save_reminders(reminders)

# 🚀 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот-напоминалка. Используй /set, чтобы добавить напоминание.")

# 📝 Команда /set YYYY-MM-DD HH:MM ТЕКСТ
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_chat.id
        args = context.args

        if len(args) < 3:
            raise ValueError("Недостаточно аргументов")

        date_str = args[0]
        time_str = args[1]
        text = ' '.join(args[2:])
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if dt < datetime.now():
            await update.message.reply_text("❌ Напоминание не может быть в прошлом.")
            return

        # Сохраняем напоминание
        user_id_str = str(user_id)
        reminders.setdefault(user_id_str, []).append({
            "datetime": dt.strftime("%Y-%m-%d %H:%M"),
            "text": text
        })
        save_reminders(reminders)

        # Добавляем задачу в планировщик
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=dt,
            args=[context, user_id, text]
        )

        await update.message.reply_text(f"✅ Напоминание установлено на {dt.strftime('%Y-%m-%d %H:%M')} — «{text}»")

    except Exception as e:
        await update.message.reply_text("❌ Ошибка! Используй формат: /set 2025-06-23 14:30 Позвонить маме")

# 📋 Команда /list
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    if user_id not in reminders or len(reminders[user_id]) == 0:
        await update.message.reply_text("У тебя нет активных напоминаний.")
        return

    message = "📋 Твои напоминания:\n"
    for idx, r in enumerate(reminders[user_id], 1):
        message += f"{idx}) {r['datetime']} — {r['text']}\n"

    await update.message.reply_text(message)

# ❌ Команда /delete НОМЕР
async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_chat.id)
        if user_id not in reminders or len(reminders[user_id]) == 0:
            await update.message.reply_text("❌ У тебя нет напоминаний.")
            return

        index = int(context.args[0]) - 1
        deleted = reminders[user_id].pop(index)
        save_reminders(reminders)

        await update.message.reply_text(f"✅ Удалено: {deleted['datetime']} — {deleted['text']}")
    except:
        await update.message.reply_text("❌ Используй: /delete НОМЕР (например, /delete 1)")

# ▶️ Запуск бота
async def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set", set_reminder))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("delete", delete_reminder))

    print("✅ Бот запущен...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
