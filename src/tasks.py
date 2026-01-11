import discord
from discord.ext import tasks, commands
import logging
import aiosqlite
from .bot import bot, update_roles_for_user

logger = logging.getLogger(__name__)

@tasks.loop(minutes=15)
async def sync_roles_task():
    logger.info("Starting background role sync...")
    
    # 1. Get all verified users
    async with aiosqlite.connect(bot.db.db_path) as db:
        async with db.execute("SELECT discord_id, wallet_address FROM users") as cursor:
            users = await cursor.fetchall()
            
    for row in users:
        discord_id = row[0]
        wallet_address = row[1]
        
        # 2. Find guild member
        # We iterate over all guilds the bot is in (usually just one)
        for guild in bot.guilds:
            member = guild.get_member(discord_id)
            if member:
                try:
                    await update_roles_for_user(member, wallet_address)
                except Exception as e:
                    logger.error(f"Error syncing user {discord_id}: {e}")
                    
    logger.info("Background role sync completed.")

@sync_roles_task.before_loop
async def before_sync_roles_task():
    await bot.wait_until_ready()

def start_background_tasks():
    sync_roles_task.start()
