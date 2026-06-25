"""
🎁 Greeting Telegram Bot — Главное приложение

Улучшенная версия с:
• Модульной структурой (create_card.py + send_cards.py)
• SQLite логированием
• Rate limiting (защита от спама)
• Админ-командой /stats
• Командой /history (мои открытки)
• Полноценными переводами RU/EN

Запуск: python greeting_app.py
"""
import logging
from dotenv import load_dotenv
import os
load_dotenv()
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
    CallbackContext
)

from create_card import create_card
from send_cards import log_user, get_user_cards, get_stats, init_db, log_card

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("6701996903:AAG86hAkmORtKPQ-HYpZLquM9hiBNGoEKkg")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))

# Состояния диалога
WAITING_NAME = 1

# Хранилище для rate limit: {user_id: timestamp}
_user_last_message = {}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def _check_rate_limit(user_id: int) -> bool:
    """Проверяет, не превысил ли пользователь лимит сообщений."""
    now = time.time()
    if user_id in _user_last_message:
        if now - _user_last_message[user_id] < 60 / RATE_LIMIT:
            return False
    _user_last_message[user_id] = now
    return True


def _is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in ADMIN_IDS


def _get_lang(update: Update) -> str:
    """Определяет язык пользователя."""
    lang = update.effective_user.language_code or "en"
    return "ru" if lang.startswith("ru") else "en"


# === ПЕРЕВОДЫ ===
TEXTS = {
    "ru": {
        "welcome": "👋 Привет, {name}! Я бот-поздравлялка! 🎉",
        "choose": "Выбери праздник ниже 👇",
        "help": """📖 <b>Как пользоваться ботом:</b>

1️⃣ Нажми на кнопку или отправь команду
2️⃣ Введи имя получателя
3️⃣ Бот создаст и отправит открытку!

<b>Команды:</b>
• /birthday Имя — День Рождения
• /newyear Имя — Новый Год
• /christmas Имя — Рождество
• /hello — Поздороваться
• /history — Мои открытки
• /stats — Статистика (админ)

💡 <i>Совет:</i> Имя можно писать на русском или английском!""",
        "hello": "👋 Привет, {name}!\n\nЯ — бот, который создаёт красивые поздравительные открытки! 🎁\nВыбери праздник и отправь открытку другу!",
        "enter_birthday": "🎂 Введи имя именинника:",
        "enter_newyear": "🎄 Введи имя получателя:",
        "enter_christmas": "🎅 Введи имя получателя:",
        "creating": "⏳ Создаю открытку...",
        "caption_birthday": "🎉 С Днём Рождения!",
        "caption_newyear": "🎄 С Новым Годом!",
        "caption_christmas": "🎅 С Рождеством!",
        "for": "Для: {name}",
        "another": "Хочешь ещё открытку?",
        "error": "❌ Произошла ошибка. Попробуй ещё раз!",
        "cancelled": "❌ Отменено.",
        "rate_limit": "⚠️ Слишком быстро! Подожди немного.",
        "no_history": "У тебя пока нет созданных открыток. Создай первую! 🎁",
        "history_title": "📜 Твои открытки:",
        "stats_title": "📊 Статистика бота",
        "stats_users": "Пользователей",
        "stats_cards": "Открыток создано",
        "stats_by": "По праздникам",
        "admin_only": "⛔ Доступ запрещён.",
        "unknown": "Я не понял. Выбери праздник ниже 👇",
        "btn_birthday": "🎂 День Рождения",
        "btn_newyear": "🎄 Новый Год",
        "btn_christmas": "🎅 Рождество",
        "btn_back": "🔙 Назад",
    },
    "en": {
        "welcome": "👋 Hello, {name}! I'm a greeting bot! 🎉",
        "choose": "Choose an occasion below 👇",
        "help": """📖 <b>How to use the bot:</b>

1️⃣ Press a button or send a command
2️⃣ Enter the recipient's name
3️⃣ The bot will create and send a card!

<b>Commands:</b>
• /birthday Name — Birthday
• /newyear Name — New Year
• /christmas Name — Christmas
• /hello — Say hello
• /history — My cards
• /stats — Statistics (admin)

💡 <i>Tip:</i> Name can be in Russian or English!""",
        "hello": "👋 Hello, {name}!\n\nI'm a bot that creates beautiful greeting cards! 🎁\nChoose an occasion and send a card to a friend!",
        "enter_birthday": "🎂 Enter the birthday person's name:",
        "enter_newyear": "🎄 Enter the recipient's name:",
        "enter_christmas": "🎅 Enter the recipient's name:",
        "creating": "⏳ Creating card...",
        "caption_birthday": "🎉 Happy Birthday!",
        "caption_newyear": "🎄 Happy New Year!",
        "caption_christmas": "🎅 Merry Christmas!",
        "for": "For: {name}",
        "another": "Want another card?",
        "error": "❌ An error occurred. Please try again!",
        "cancelled": "❌ Cancelled.",
        "rate_limit": "⚠️ Too fast! Please wait a bit.",
        "no_history": "You don't have any cards yet. Create your first one! 🎁",
        "history_title": "📜 Your cards:",
        "stats_title": "📊 Bot Statistics",
        "stats_users": "Users",
        "stats_cards": "Cards created",
        "stats_by": "By occasion",
        "admin_only": "⛔ Access denied.",
        "unknown": "I didn't understand. Choose an occasion below 👇",
        "btn_birthday": "🎂 Birthday",
        "btn_newyear": "🎄 New Year",
        "btn_christmas": "🎅 Christmas",
        "btn_back": "🔙 Back",
    }
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Возвращает перевод по ключу."""
    text = TEXTS.get(lang, TEXTS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# === КЛАВИАТУРЫ ===
def main_menu(lang: str) -> InlineKeyboardMarkup:
    """Главное меню с выбором праздника."""
    keyboard = [
        [InlineKeyboardButton(t("btn_birthday", lang), callback_data="birthday")],
        [InlineKeyboardButton(t("btn_newyear", lang), callback_data="newyear")],
        [InlineKeyboardButton(t("btn_christmas", lang), callback_data="christmas")],
    ]
    return InlineKeyboardMarkup(keyboard)


def again_menu(lang: str) -> InlineKeyboardMarkup:
    """Меню после отправки открытки."""
    keyboard = [
        [InlineKeyboardButton(t("btn_birthday", lang), callback_data="birthday")],
        [InlineKeyboardButton(t("btn_newyear", lang), callback_data="newyear")],
        [InlineKeyboardButton(t("btn_christmas", lang), callback_data="christmas")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="hello")],
    ]
    return InlineKeyboardMarkup(keyboard)


# === ОБРАБОТЧИКИ КОМАНД ===
async def start(update: Update, _context: CallbackContext):
    """Приветствие + главное меню."""
    user = update.effective_user
    lang = _get_lang(update)

    if not _check_rate_limit(user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return

    log_user(user.id, user.username, user.first_name, lang)

    welcome = t("welcome", lang, name=user.first_name)
    choose = t("choose", lang)
    await update.message.reply_text(f"{welcome}\n\n{choose}", reply_markup=main_menu(lang))


async def help_command(update: Update, _context: CallbackContext):
    """Справка по использованию бота."""
    lang = _get_lang(update)
    if not _check_rate_limit(update.effective_user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return
    await update.message.reply_text(t("help", lang), parse_mode="HTML")


async def hello(update: Update, _context: CallbackContext):
    """Просто поздороваться + показать меню."""
    lang = _get_lang(update)
    if not _check_rate_limit(update.effective_user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return
    text = t("hello", lang, name=update.effective_user.first_name)
    await update.message.reply_text(text, reply_markup=main_menu(lang))


async def history(update: Update, _context: CallbackContext):
    """Показывает историю созданных открыток пользователя."""
    lang = _get_lang(update)
    user_id = update.effective_user.id

    rows = get_user_cards(user_id)

    if not rows:
        await update.message.reply_text(t("no_history", lang))
        return

    text = t("history_title", lang) + "\n\n"
    emojis = {"birthday": "🎂", "newyear": "🎄", "christmas": "🎅"}
    for occasion, name, created_at in rows:
        text += f"{emojis.get(occasion, '🎁')} {name} — {created_at}\n"

    await update.message.reply_text(text)


async def stats(update: Update, _context: CallbackContext):
    """Статистика бота (только для администраторов)."""
    lang = _get_lang(update)
    user_id = update.effective_user.id

    if not _is_admin(user_id):
        await update.message.reply_text(t("admin_only", lang))
        return

    s = get_stats()
    text = f"📊 <b>{t('stats_title', lang)}</b>\n\n"
    text += f"👤 {t('stats_users', lang)}: {s['users']}\n"
    text += f"🖼 {t('stats_cards', lang)}: {s['cards']}\n\n"
    text += f"<b>{t('stats_by', lang)}:</b>\n"
    emojis = {"birthday": "🎂", "newyear": "🎄", "christmas": "🎅"}
    for occasion, count in s['by_occasion'].items():
        text += f"{emojis.get(occasion, '🎁')} {occasion}: {count}\n"

    await update.message.reply_text(text, parse_mode="HTML")


# === ДИАЛОГИ СОЗДАНИЯ ОТКРЫТОК ===
async def cmd_birthday(update: Update, context: CallbackContext):
    """Команда /birthday [имя] — запускает диалог или сразу создаёт открытку."""
    lang = _get_lang(update)
    if not _check_rate_limit(update.effective_user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return ConversationHandler.END

    if context.args:
        await _send_card(update, context, " ".join(context.args), "birthday")
        return ConversationHandler.END

    context.user_data["occasion"] = "birthday"
    await update.message.reply_text(t("enter_birthday", lang))
    return WAITING_NAME


async def cmd_newyear(update: Update, context: CallbackContext):
    """Команда /newyear [имя] — запускает диалог или сразу создаёт открытку."""
    lang = _get_lang(update)
    if not _check_rate_limit(update.effective_user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return ConversationHandler.END

    if context.args:
        await _send_card(update, context, " ".join(context.args), "newyear")
        return ConversationHandler.END

    context.user_data["occasion"] = "newyear"
    await update.message.reply_text(t("enter_newyear", lang))
    return WAITING_NAME


async def cmd_christmas(update: Update, context: CallbackContext):
    """Команда /christmas [имя] — запускает диалог или сразу создаёт открытку."""
    lang = _get_lang(update)
    if not _check_rate_limit(update.effective_user.id):
        await update.message.reply_text(t("rate_limit", lang))
        return ConversationHandler.END

    if context.args:
        await _send_card(update, context, " ".join(context.args), "christmas")
        return ConversationHandler.END

    context.user_data["occasion"] = "christmas"
    await update.message.reply_text(t("enter_christmas", lang))
    return WAITING_NAME


async def receive_name(update: Update, context: CallbackContext):
    """Получает имя в режиме диалога и отправляет открытку."""
    name = update.message.text.strip()
    occasion = context.user_data.get("occasion", "birthday")
    await _send_card(update, context, name, occasion)
    return ConversationHandler.END


async def _send_card(update: Update, context: CallbackContext, name: str, occasion: str):
    """Внутренняя функция: создаёт и отправляет открытку."""
    lang = _get_lang(update)
    user_id = update.effective_user.id

    loading = await update.message.reply_text(t("creating", lang))

    try:
        card_path = create_card(name, occasion, lang)

        captions = {
            "birthday": t("caption_birthday", lang),
            "newyear": t("caption_newyear", lang),
            "christmas": t("caption_christmas", lang),
        }
        caption = f"{captions.get(occasion, '🎁')}\n\n{t('for', lang, name=name)}"

        with open(card_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=caption)

        # Логируем в БД и очищаем состояние
        log_card(user_id, occasion, name)
        context.user_data.pop("occasion", None)

        await loading.delete()
        await update.message.reply_text(t("another", lang), reply_markup=again_menu(lang))

    except (TelegramError, OSError, IOError) as e:
        logger.error(f"Ошибка создания/отправки: {e}", exc_info=True)
        try:
            await loading.edit_text(t("error", lang))
        except (TelegramError, OSError, IOError):
            pass


# === CALLBACKS (кнопки) ===
async def button_handler(update: Update, context: CallbackContext):
    """Обрабатывает нажатия inline-кнопок."""
    query = update.callback_query
    await query.answer()

    data = query.data
    lang = _get_lang(update)

    if data == "hello":
        text = t("hello", lang, name=update.effective_user.first_name)
        await query.edit_message_text(text, reply_markup=main_menu(lang))
        return ConversationHandler.END

    if data in ("birthday", "newyear", "christmas"):
        context.user_data["occasion"] = data
        prompts = {
            "birthday": t("enter_birthday", lang),
            "newyear": t("enter_newyear", lang),
            "christmas": t("enter_christmas", lang),
        }
        await query.edit_message_text(prompts[data])
        return WAITING_NAME

    return ConversationHandler.END


# === ОБРАБОТКА ТЕКСТА ===
async def text_handler(update: Update, _context: CallbackContext):
    """Обрабатывает обычный текст вне диалога."""
    lang = _get_lang(update)
    await update.message.reply_text(t("unknown", lang), reply_markup=main_menu(lang))


async def cancel(update: Update, context: CallbackContext):
    """Отмена текущего диалога."""
    lang = _get_lang(update)
    context.user_data.pop("occasion", None)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    print("🚀 Запускаю бота...")
    print("Для остановки нажми Ctrl+C")

    # Инициализация базы данных
    init_db()

    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения!")
        print("Создай файл .env с содержимым:")
        print("BOT_TOKEN=your_token_here")
        print("ADMIN_IDS=your_telegram_id")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler для создания открыток
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("birthday", cmd_birthday),
            CommandHandler("newyear", cmd_newyear),
            CommandHandler("christmas", cmd_christmas),
            CallbackQueryHandler(button_handler, pattern="^(birthday|newyear|christmas|hello)$"),
        ],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("hello", hello))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()