import logging
import asyncio
from src.config import DISCORD_TOKEN
from src.bot import bot
from src.tasks import start_background_tasks

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables.")
        return

    async with bot:
        start_background_tasks()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
