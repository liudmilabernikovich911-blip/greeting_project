import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from bot import get_application
from telegram import Update

logger = logging.getLogger(__name__)

# Создаём бота один раз при импорте
application = get_application()


@asynccontextmanager
async def lifespan():
    """Startup + shutdown через lifespan."""
    # Startup
    await application.initialize()
    await application.start()

    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if render_host:
        webhook_url = f"https://{render_host}/webhook"
    else:
        base = os.getenv("WEBHOOK_URL", "")
        webhook_url = f"{base}/webhook" if base else ""

    if webhook_url and webhook_url != "/webhook":
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook установлен: {webhook_url}")
    else:
        logger.warning("Webhook URL не установлен!")

    yield

    # Shutdown
    await application.stop()
    await application.shutdown()
    logger.info("Бот остановлен.")


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    """Принимает обновления от Telegram."""
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


@app.get("/")
async def health():
    """Health-check для Render."""
    return {"status": "ok", "bot": "running"}