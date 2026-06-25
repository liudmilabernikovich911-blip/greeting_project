"""
Генератор поздравительных открыток.
Создаёт красивые изображения с рамками, шрифтами и градиентами.
Сохраняет в папку dist/
"""
from dotenv import load_dotenv
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
load_dotenv()  # Загружает переменные из .env

BOT_TOKEN = os.getenv("6701996903:AAG86hAkmORtKPQ-HYpZLquM9hiBNGoEKkg")
ADMIN_IDS = os.getenv("1050111550")

# Папка для готовых открыток
CARDS_DIR = Path("dist")
CARDS_DIR.mkdir(parents=True, exist_ok=True)


def get_fonts():
    """Пытается найти системные шрифты, иначе использует стандартный."""
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
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
            except Exception:
                continue

    default = ImageFont.load_default()
    return {'large': default, 'medium': default, 'small': default}


def detect_language(text: str) -> str:
    """Определяет язык по имени (русский или английский)."""
    for char in text:
        if '\u0400' <= char <= '\u04FF':
            return 'ru'
    return 'en'


def create_card(name: str, occasion: str = "birthday", language: str = None) -> str:
    """
    Создаёт поздравительную открытку.

    Args:
        name: Имя получателя
        occasion: Тип праздника (birthday, newyear, christmas)
        language: Язык (ru, en). Если None — автоопределение.

    Returns:
        Путь к созданному изображению.
    """
    if language is None:
        language = detect_language(name)

    themes = {
        "birthday": {
            "bg": "#FFE4E1", "border": "#FF69B4",
            "title_color": "#C71585", "name_color": "#8B008B", "text_color": "#4B0082",
            "ru": {
                "title": " С Днём Рождения! ",
                "wishes": ["Желаю счастья, здоровья,", "успехов во всех начинаниях", "и исполнения всех желаний!"]
            },
            "en": {
                "title": " Happy Birthday! ",
                "wishes": ["Wishing you happiness, health,", "success in all your endeavors", "and all your dreams come true!"]
            }
        },
        "newyear": {
            "bg": "#E0F7FA", "border": "#00BCD4",
            "title_color": "#006064", "name_color": "#00838F", "text_color": "#004D40",
            "ru": {
                "title": " С Новым Годом! ❄️",
                "wishes": ["Пусть этот год принесёт", "радость, удачу и тепло!", "Счастья тебе и близким!"]
            },
            "en": {
                "title": " Happy New Year! ❄️",
                "wishes": ["May this year bring you", "joy, luck and warmth!", "Happiness to you and your loved ones!"]
            }
        },
        "christmas": {
            "bg": "#E8F5E9", "border": "#4CAF50",
            "title_color": "#1B5E20", "name_color": "#2E7D32", "text_color": "#33691E",
            "ru": {
                "title": " С Рождеством! ",
                "wishes": ["Пусть в этот волшебный день", "сбудутся все твои мечты!", "Мира и добра тебе!"]
            },
            "en": {
                "title": " Merry Christmas! ",
                "wishes": ["May all your dreams come true", "on this magical day!", "Peace and joy to you!"]
            }
        }
    }

    theme = themes.get(occasion, themes["birthday"])
    lang_data = theme.get(language, theme["ru"])

    # Создаём изображение 800x600
    img = Image.new('RGB', (800, 600), color=theme["bg"])
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Рамка
    draw.rectangle([20, 20, 780, 580], outline=theme["border"], width=5)

    # Заголовок
    title = lang_data["title"]
    bbox = draw.textbbox((0, 0), title, font=fonts['large'])
    x = (800 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 100), title, fill=theme["title_color"], font=fonts['large'])

    # Имя
    name_text = f"Dear {name}!" if language == "en" else f"Дорогой(ая) {name}!"
    bbox = draw.textbbox((0, 0), name_text, font=fonts['medium'])
    x = (800 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 250), name_text, fill=theme["name_color"], font=fonts['medium'])

    # Пожелания
    y = 350
    for line in lang_data["wishes"]:
        bbox = draw.textbbox((0, 0), line, font=fonts['small'])
        x = (800 - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=theme["text_color"], font=fonts['small'])
        y += 50

    # Сохраняем
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = CARDS_DIR / f"card_{occasion}_{safe_name}.png"
    img.save(filename)
    print(f"✅ Открытка создана: {filename}")
    return str(filename)


if __name__ == "__main__":
    print("Тестовая генерация открыток...")
    create_card("Graham", "birthday")
    create_card("Melanie", "birthday")
    create_card("Emy", "birthday")
    create_card("Melanie", "newyear", "en")
    create_card("Emy", "christmas")
    print("Готово! Проверь папку dist/")