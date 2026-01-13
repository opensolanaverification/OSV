import discord
from discord.ext import tasks, commands
import logging
import aiosqlite
from .bot import bot, update_roles_for_user

logger = logging.getLogger(__name__)

@tasks.loop(minutes=5)
async def sync_roles_task():
    logger.info("Starting background role sync...")
    
    try:
        # 1. Fetch all managed role IDs from tiers across all collections
        async with aiosqlite.connect(bot.db.db_path) as db:
            async with db.execute("SELECT DISTINCT role_id FROM tiers") as cursor:
                rows = await cursor.fetchall()
                managed_role_ids = {row[0] for row in rows}
        
        if not managed_role_ids:
            logger.info("No managed roles found in tiers. Skipping sync.")
            return

        # 2. Iterate through all guilds and members
        for guild in bot.guilds:
            for member in guild.members:
                # Check if the member has ANY of the roles we manage
                has_managed_role = any(r.id in managed_role_ids for r in member.roles)
                
                # Also check if they are in our users table (to add roles if they should have them)
                user_record = await bot.db.get_user(member.id)
                
                if has_managed_role or user_record:
                    # Sync roles (RoleEngine handles None wallet by returning removals)
                    wallet_address = user_record[1] if user_record else None
                    try:
                        await update_roles_for_user(member, wallet_address)
                    except Exception as e:
                        logger.error(f"Error syncing user {member.id}: {e}")
                        
    except Exception as e:
        logger.error(f"Global sync task error: {e}")
                    
    logger.info("Background role sync completed.")

@sync_roles_task.before_loop
async def before_sync_roles_task():
    await bot.wait_until_ready()

def start_background_tasks():
    sync_roles_task.start()
