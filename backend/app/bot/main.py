import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.bot.handlers import user, submit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

async def start_bot():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Bot startup aborted.")
        return
        
    logger.info("Initializing Telegram Bot...")
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # Using simple in-memory storage for FSM states
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    dp.include_router(submit.router) # Submission FSM must be checked first
    dp.include_router(user.router)
    
    logger.info("Bot starting in polling mode...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot execution error: {e}", exc_info=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(start_bot())
