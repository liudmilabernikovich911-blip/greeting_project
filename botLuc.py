from dotenv import load_dotenv
load_dotenv()  # Загружает переменные из .env файла

import telebot
import os
import sys

# ─── Пути для соседних папок ───
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from create_card.create_card import create_card
except ImportError:
    from create_card import create_card

# ─── Токен из переменной окружения или .env ───
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set! Add it to environment variables or .env file.")

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
        occasion = parts[2] if len(parts) > 2 else "weedbook"

        bot.send_message(
            message.chat.id,
            f"⏳ Creating a {occasion} card for {name}..."
        )

        photo_path = create_card(name, occasion)

        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=f"🎉 {occasion.title()} card for {name}!"
            )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")


# ─── Запуск ───
print("Bot is running...")
bot.polling(none_stop=True)