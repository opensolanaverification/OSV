import discord
from discord.ext import tasks, commands
import logging
import aiosqlite
from .bot import bot, update_roles_for_user, apply_role_changes

logger = logging.getLogger(__name__)

@tasks.loop(minutes=5)
async def sync_roles_task():
    logger.info("Starting background role sync (collection-based)...")
    
    try:
        # 1. Fetch global holdings (once per sync loop)
        global_holdings = await bot.role_engine.get_global_holdings()
        
        # 2. Fetch all collections and managed roles
        all_collections = await bot.db.get_all_collections()
        async with aiosqlite.connect(bot.db.db_path) as db:
            async with db.execute("SELECT DISTINCT role_id FROM tiers") as cursor:
                rows = await cursor.fetchall()
                managed_role_ids = {row[0] for row in rows}
        
        if not managed_role_ids:
            logger.info("No managed roles found. Skipping sync.")
            return

        # 3. Iterate through all members and sync based on global holdings
        for guild in bot.guilds:
            for member in guild.members:
                # Check if member has managed roles or is in our linked users
                has_managed_role = any(r.id in managed_role_ids for r in member.roles)
                user_record = await bot.db.get_user(member.id)
                
                if has_managed_role or user_record:
                    wallet_address = user_record[1] if user_record else None
                    
                    # Get this specific user's holdings from our global map
                    user_holdings = global_holdings.get(wallet_address, {}) if wallet_address else {}
                    
                    # Calculate and apply
                    try:
                        to_add, to_remove = await bot.role_engine.calculate_roles_from_holdings(user_holdings, all_collections)
                        await apply_role_changes(member, to_add, to_remove)
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
