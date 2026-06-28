"""
Генератор поздравительных открыток в Telegram (Webhook-режим).

Команды:
/start — приветствие
/card <имя> <праздник> — создать открытку

Архитектура: FastAPI принимает webhook от Telegram →
→ python-telegram-bot обрабатывает update →
→ генерируется открытка и отправляется пользователю.
"""
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, Request
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
PORT = int(os.getenv("PORT", 8000))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Задай переменную окружения.")
if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL не найден! Пример: https://your-service.onrender.com/webhook")

CARDS_DIR = Path("dist")
CARDS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ ГЕНЕРАТОР ОТКРЫТОК ============

def get_fonts():
    """Ищет системные шрифты (Render — Ubuntu/Debian)."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return {
                    'large': ImageFont.truetype(path, 60),
                    'medium': ImageFont.truetype(path, 40),
                    'small': ImageFont.truetype(path, 30)
                }
            except OSError:
                continue
    default = ImageFont.load_default()
    return {'large': default, 'medium': default, 'small': default}


def detect_language(text: str) -> str:
    for char in text:
        if '\u0400' <= char <= '\u04FF':
            return 'ru'
    return 'en'


def create_card(name: str, occasion: str = "birthday", language: str = None) -> str:
    if language is None:
        language = detect_language(name)

    themes = {
        "birthday": {
            "bg": "#FFE4E1", "border": "#FF69B4",
            "title_color": "#C71585", "name_color": "#8B008B", "text_color": "#4B0082",
            "ru": {"title": "🎉 С Днём Рождения! 🎂",
                   "wishes": ["Желаю счастья, здоровья,", "успехов во всех начинаниях", "и исполнения всех желаний!"]},
            "en": {"title": "🎉 Happy Birthday! 🎂",
                   "wishes": ["Wishing you happiness, health,", "success in all your endeavors",
                              "and all your dreams come true!"]}
        },
        "newyear": {
            "bg": "#E0F7FA", "border": "#00BCD4",
            "title_color": "#006064", "name_color": "#00838F", "text_color": "#004D40",
            "ru": {"title": "❄️ С Новым Годом! 🎄",
                   "wishes": ["Пусть этот год принесёт", "радость, удачу и тепло!", "Счастья тебе и близким!"]},
            "en": {"title": "❄️ Happy New Year! 🎄", "wishes": ["May this year bring you", "joy, luck and warmth!",
                                                               "Happiness to you and your loved ones!"]}
        },
        "christmas": {
            "bg": "#E8F5E9", "border": "#4CAF50",
            "title_color": "#1B5E20", "name_color": "#2E7D32", "text_color": "#33691E",
            "ru": {"title": "🎄 С Рождеством! ⭐",
                   "wishes": ["Пусть в этот волшебный день", "сбудутся все твои мечты!", "Мира и добра тебе!"]},
            "en": {"title": "🎄 Merry Christmas! ⭐",
                   "wishes": ["May all your dreams come true", "on this magical day!", "Peace and joy to you!"]}
        }
    }

    theme = themes.get(occasion, themes["birthday"])
    lang_data = theme.get(language, theme["ru"])

    img = Image.new('RGB', (800, 600), color=theme["bg"])
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Рамка
    draw.rectangle([20, 20, 780, 580], outline=theme["border"], width=5)

    # Заголовок
    title = lang_data["title"]
    bbox = draw.textbbox((0, 0), title, font=fonts['large'])
    x = (800 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 80), title, fill=theme["title_color"], font=fonts['large'])

    # Имя
    name_text = f"Dear {name}!" if language == "en" else f"Дорогой(ая) {name}!"
    bbox = draw.textbbox((0, 0), name_text, font=fonts['medium'])
    x = (800 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 220), name_text, fill=theme["name_color"], font=fonts['medium'])

    # Пожелания
    y = 320
    for line in lang_data["wishes"]:
        bbox = draw.textbbox((0, 0), line, font=fonts['small'])
        x = (800 - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=theme["text_color"], font=fonts['small'])
        y += 50

    # Сохраняем
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = CARDS_DIR / f"card_{occasion}_{safe_name}.png"
    img.save(filename)
    return str(filename)


# ============ TELEGRAM HANDLERS ============

async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I make congratulations cards!\n\n"
        "📋 Commands:\n"
        "/card <name> <holiday> — create a card\n\n"
        "Examples:\n"
        "/card Graham birthday\n"
        "/card Melanie birthday\n"
        "/card Emy birthday\n"
        "/card Melanie newyear\n"
        "/card Emy christmas\n\n"
        "Holidays: birthday, newyear, christmas"
    )


async def make_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        await update.message.reply_text(
            "❌ Укажи имя!\n"
            "Пример: /card Алекс birthday\n\n"
            "Доступные праздники: birthday, newyear, christmas"
        )
        return

    name = args[0]
    occasion = args[1] if len(args) > 1 else "birthday"

    valid_occasions = ["birthday", "newyear", "christmas"]
    if occasion not in valid_occasions:
        await update.message.reply_text(
            f"❌ Неизвестный праздник: {occasion}\n"
            f"Доступные: {', '.join(valid_occasions)}"
        )
        return

    msg = await update.message.reply_text("🎨 Создаю открытку...")

    try:
        filepath = create_card(name, occasion)

        with open(filepath, 'rb') as photo:
            await update.message.reply_photo(photo=photo)

        await msg.delete()
        logger.info("Открытка создана для %s: %s", update.effective_user.id, filepath)

    except (OSError, ValueError, TelegramError) as e:
        await msg.edit_text(f"❌ Ошибка: {e}")
        logger.error("Ошибка в make_card: %s", e)


async def unknown(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я понимаю только команды.\n"
        "Напиши /start для справки."
    )


# ============ FASTAPI + WEBHOOK ============

# Создаём Application PTB (без run_polling!)
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("card", make_card))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))


@asynccontextmanager
async def lifespan():
    """Управление жизненным циклом: старт / стоп PTB."""
    # Startup
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    yield
    # Shutdown
    await application.stop()
    await application.shutdown()
    logger.info("🛑 Приложение остановлено")


fastapi_app = FastAPI(
    title="Telegram Card Bot",
    description="Webhook-сервер для генерации поздравительных открыток",
    lifespan=lifespan
)


@fastapi_app.post("/webhook")
async def webhook(request: Request):
    """Принимает updates от Telegram."""
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}


@fastapi_app.get("/")
async def health():
    """Health-check для Render (и для ручной проверки)."""
    return {"status": "alive", "service": "telegram-card-bot", "mode": "webhook"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=PORT)