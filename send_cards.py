"""
Модуль логирования пользователей и открыток в SQLite.
Отправка открыток делегирована greeting_app.py (через python-telegram-bot Application).
"""
import os
import sqlite3
import logging
from pathlib import Path


from datetime import datetime

logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
DB_PATH = Path(os.getenv("DB_PATH", "dist/greetings.db"))


# === DATABASE ===
def init_db():
    """Создаёт таблицы, если их нет."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            occasion TEXT,
            recipient_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_user(user_id: int, username: str, first_name: str, language: str):
    """Логирует пользователя в базу. Сохраняет created_at при первой записи."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name, language, created_at)
        VALUES (?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM users WHERE user_id = ?), CURRENT_TIMESTAMP
        ))
    """, (user_id, username, first_name, language, user_id))
    conn.commit()
    conn.close()


def log_card(user_id: int, occasion: str, recipient_name: str):
    """Логирует создание открытки."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO cards (user_id, occasion, recipient_name) VALUES (?, ?, ?)",
        (user_id, occasion, recipient_name)
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Возвращает статистику бота."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM cards")
    cards = c.fetchone()[0]
    c.execute("SELECT occasion, COUNT(*) FROM cards GROUP BY occasion")
    by_occasion = c.fetchall()
    conn.close()
    return {"users": users, "cards": cards, "by_occasion": dict(by_occasion)}


def get_user_cards(user_id: int) -> list:
    """Возвращает историю открыток пользователя."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT occasion, recipient_name, created_at FROM cards
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("✅ База данных инициализирована")
    print(f"📊 Статистика: {get_stats()}")