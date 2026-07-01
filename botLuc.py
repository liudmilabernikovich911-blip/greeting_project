from dotenv import load_dotenv

load_dotenv()

import telebot
import os
import sys

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Any

# ─── Пути для соседних папок ───
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from create_card.create_card import create_card
except ImportError:
    from create_card import create_card

# ─── Токен ───
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set! Add it to .env or environment variables.")

bot = telebot.TeleBot(BOT_TOKEN)

# ─── Хранилище состояний пользователей ───
user_states: Dict[int, Dict[str, Any]] = {}

HOLIDAYS = {
    'birthday': 'Birthday',
    'newyear': 'New Year',
    'christmas': 'Christmas',
    'weedbook': 'Weedbook'
}


# ═══════════════════════════════════════
# HTTP Keep-Alive сервер (для cron-job.org)
# ═══════════════════════════════════════
class PingHandler(BaseHTTPRequestHandler):
    def do_get(self) -> None:
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # тихий режим, не спамит в консоль


def run_http_server(srv_port: int = 8080) -> None:
    server = HTTPServer(('0.0.0.0', srv_port), PingHandler)  # type: ignore[arg-type]
    print(f"Keep-alive HTTP server running on port {srv_port}")
    server.serve_forever()


# ═══════════════════════════════════════
# Команды бота
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def send_welcome(message) -> None:
    bot.send_message(
        message.chat.id,
        "🎉 <b>Welcome to the Greeting Card Bot!</b>\n\n"
        "I can create beautiful cards step by step.\n\n"
        "<b>Commands:</b>\n"
        "/makecard — interactive mode (asks name & holiday)\n"
        "/card &lt;name&gt; &lt;holiday&gt; — quick mode\n\n"
        "<b>Available holidays:</b>\n"
        "• birthday\n"
        "• newyear\n"
        "• christmas\n"
        "• weedbook\n\n"
        "Example quick: <code>/card Graham birthday</code>",
        parse_mode='HTML'
    )


@bot.message_handler(commands=['makecard'])
def start_makecard(message) -> None:
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 'name'}

    bot.send_message(
        chat_id,
        "📝 <b>Step 1 of 2</b>\nPlease enter the <b>name</b> for the card:",
        parse_mode='HTML'
    )


@bot.message_handler(commands=['card'])
def handle_card_quick(message) -> None:
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(
                message.chat.id,
                "❌ Format: /card <name> <holiday>\n"
                "Example: /card Graham birthday\n\n"
                "Or use /makecard for interactive mode."
            )
            return

        name = parts[1]
        occasion = parts[2] if len(parts) > 2 else "weedbook"

        if occasion.lower() not in HOLIDAYS:
            bot.send_message(
                message.chat.id,
                f"⚠️ Unknown holiday: <b>{occasion}</b>\n"
                f"Available: {', '.join(HOLIDAYS.keys())}",
                parse_mode='HTML'
            )
            return

        _create_and_send_card(message.chat.id, name, occasion)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")


@bot.message_handler(func=lambda msg: msg.chat.id in user_states)
def handle_state_input(message) -> None:
    chat_id = message.chat.id
    state = user_states[chat_id]
    text = message.text.strip()

    if state['step'] == 'name':
        state['name'] = text
        state['step'] = 'holiday'

        holidays_text = '\n'.join([f"• {k}" for k in HOLIDAYS.keys()])
        bot.send_message(
            chat_id,
            f"✅ Name set: <b>{text}</b>\n\n"
            f"📝 <b>Step 2 of 2</b>\nChoose a holiday:\n{holidays_text}\n\n"
            f"(You can also type <code>weedbook</code> 😉)",
            parse_mode='HTML'
        )

    elif state['step'] == 'holiday':
        occasion = text.lower()

        if occasion not in HOLIDAYS:
            bot.send_message(
                chat_id,
                f"⚠️ Unknown holiday: <b>{text}</b>\n"
                f"Please choose from: {', '.join(HOLIDAYS.keys())}",
                parse_mode='HTML'
            )
            return

        name = state['name']
        del user_states[chat_id]

        _create_and_send_card(chat_id, name, occasion)


def _create_and_send_card(chat_id: int, name: str, occasion: str) -> None:
    """Создаёт карточку и отправляет в чат."""
    bot.send_message(
        chat_id,
        f"⏳ Creating a <b>{HOLIDAYS[occasion]}</b> card for <b>{name}</b>...",
        parse_mode='HTML'
    )

    try:
        photo_path = create_card(name, occasion)

        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                chat_id,
                photo,
                caption=f"🎉 <b>{HOLIDAYS[occasion]} card for {name}!</b>",
                parse_mode='HTML'
            )
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error creating card: {e}")


# ═══════════════════════════════════════
# Запуск
# ═══════════════════════════════════════
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True, interval=1)