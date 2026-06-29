import telebot
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Пробуем импорт из папки create_card/ или из той же папки
try:
    from create_card.create_card import create_card
except ImportError:
    from create_card import create_card

# ─── Токен бота ───
BOT_TOKEN = "6701996903:AAHlm7xViI2walWzusxphV549OjyMjGfWho"
TELEGRAM_BOT_TOKEN = "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"
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Hello! I make congratulations cards!\n\n"
        "Commands:\n"
        "/card <name> <holiday> — create a card\n\n"
        "Examples:\n"
        "/card Graham birthday\n"
        "/card Melanie newyear\n"
        "/card Emy christmas\n"
        "/card John weedbook\n\n"
        "Holidays: birthday, newyear, christmas, weedbook"
    )


@bot.message_handler(commands=['card'])
def handle_card(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(
                message.chat.id,
                "❌ Format: /card <name> <holiday>\n"
                "Example: /card Graham birthday"
            )
            return

        name = parts[1]
        # Если праздник не указан — по умолчанию weedbook
        occasion = parts[2] if len(parts) > 2 else "weedbook"

        bot.send_message(
            message.chat.id,
            f"⏳ Creating a {occasion} card for {name}..."
        )

        # Создаём открытку
        photo_path = create_card(name, occasion)

        # Отправляем фото в Telegram
        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=f"🎉 {occasion.title()} card for {name}!"
            )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")


# Удаляем webhook, если он был установлен (например, из другого скрипта)
bot.delete_webhook(drop_pending_updates=True)
print("Webhook deleted, switching to polling...")

# ─── Запуск ───
bot.delete_webhook(drop_pending_updates=True)
print("Bot is running...")
bot.polling(none_stop=True)
