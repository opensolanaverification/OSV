import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
import time
from typing import Optional

from .config import GUILD_ID, VERIFICATION_AMOUNT_MIN, VERIFICATION_AMOUNT_MAX, VERIFICATION_EXPIRY_SECONDS
from .db import Database
from .helius_client import HeliusClient
from .solana_verifier import SolanaVerifier
from .role_engine import RoleEngine

logger = logging.getLogger(__name__)

class NFTVerificationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        self.db = Database()
        self.helius = HeliusClient()
        self.verifier = SolanaVerifier()
        self.role_engine = RoleEngine(self.db, self.helius)
        
    async def setup_hook(self):
        await self.db.init_db()
        # Sync to specific guild for faster dev testing, or global if GUILD_ID is not set or 0
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
            
    async def close(self):
        await self.verifier.close()
        await super().close()

bot = NFTVerificationBot()

# --- User Commands ---

class VerifyModal(discord.ui.Modal, title="Verify Transaction"):
    tx_signature = discord.ui.TextInput(
        label="Transaction Signature",
        placeholder="Paste your transaction signature here...",
        required=True,
        min_length=30, # Signatures are usually longer, e.g. 88 chars
        max_length=100
    )

    def __init__(self, bot: 'NFTVerificationBot', wallet_address: str, amount: float):
        super().__init__()
        self.bot = bot
        self.wallet_address = wallet_address
        self.amount = amount

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        signature = self.tx_signature.value.strip()
        success = await self.bot.verifier.verify_transaction(signature, self.wallet_address, self.amount)
        
        if success:
            try:
                await self.bot.db.add_user(interaction.user.id, self.wallet_address)
                await self.bot.db.delete_challenge(interaction.user.id, self.wallet_address)
                await interaction.followup.send(f"Success! Wallet `{self.wallet_address}` verified.", ephemeral=True)
                
                await update_roles_for_user(interaction.user, self.wallet_address)
                
            except Exception as e:
                await interaction.followup.send(f"Error saving user: {e}", ephemeral=True)
        else:
            await interaction.followup.send("Verification failed. Please check the amount and wallet used.", ephemeral=True)

class ConnectView(discord.ui.View):
    def __init__(self, bot: 'NFTVerificationBot', wallet_address: str, amount: float):
        super().__init__(timeout=VERIFICATION_EXPIRY_SECONDS)
        self.bot = bot
        self.wallet_address = wallet_address
        self.amount = amount

    @discord.ui.button(label="Verify Transaction", style=discord.ButtonStyle.green)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = VerifyModal(self.bot, self.wallet_address, self.amount)
        await interaction.response.send_modal(modal)

@bot.tree.command(name="connect_wallet", description="Start the wallet verification process")
async def connect_wallet(interaction: discord.Interaction, wallet_address: str):
    # 1. Check if already linked
    existing = await bot.db.get_user(interaction.user.id)
    if existing:
        await interaction.response.send_message(f"You are already linked to {existing[1]}. Use `/disconnect_wallet` first.", ephemeral=True)
        return

    # 3. Generate challenge
    amount = round(random.uniform(VERIFICATION_AMOUNT_MIN, VERIFICATION_AMOUNT_MAX), 6) # 6 decimals for sufficient entropy
    expires_at = time.time() + VERIFICATION_EXPIRY_SECONDS
    
    await bot.db.create_challenge(interaction.user.id, wallet_address, amount, expires_at)
    
    msg = (
        f"**Wallet Verification**\n"
        f"To verify ownership of `{wallet_address}`, please send exactly **{amount} SOL** "
        f"from that wallet to itself (self-transfer).\n"
        f"Expires in {VERIFICATION_EXPIRY_SECONDS // 60} minutes.\n\n"
        f"Click the button below to submit your transaction signature."
    )
    
    view = ConnectView(bot, wallet_address, amount)
    await interaction.response.send_message(msg, view=view, ephemeral=True)

@bot.tree.command(name="disconnect_wallet", description="Unlink your wallet")
async def disconnect_wallet(interaction: discord.Interaction):
    await bot.db.remove_user(interaction.user.id)
    await interaction.response.send_message("Wallet disconnected. Roles will be removed on next sync.", ephemeral=True)

@bot.tree.command(name="status", description="Check your verification status")
async def status(interaction: discord.Interaction):
    user = await bot.db.get_user(interaction.user.id)
    if user:
        await interaction.response.send_message(f"Verified Wallet: `{user[1]}`", ephemeral=True)
    else:
        await interaction.response.send_message("Not verified.", ephemeral=True)

# --- Admin Commands ---

@bot.tree.command(name="add_collection", description="Admin: Add a collection to track")
@app_commands.checks.has_permissions(administrator=True)
async def add_collection(interaction: discord.Interaction, address: str, name: str):
    await bot.db.add_collection(address, name)
    await interaction.response.send_message(f"Collection `{name}` ({address}) added.", ephemeral=True)

@bot.tree.command(name="set_tier", description="Admin: Add a role tier for a collection")
@app_commands.checks.has_permissions(administrator=True)
async def set_tier(interaction: discord.Interaction, collection: str, min_nfts: int, role: discord.Role):
    await bot.db.add_tier(collection, min_nfts, role.id)
    await interaction.response.send_message(f"Tier added for `{collection}`: {min_nfts}+ NFTs -> {role.name}", ephemeral=True)

# --- Helpers ---

async def update_roles_for_user(member: discord.Member, wallet_address: str):
    roles_to_add_ids, roles_to_remove_ids = await bot.role_engine.calculate_roles(wallet_address)
    
    current_role_ids = {r.id for r in member.roles}
    
    # Add
    to_add = []
    for rid in roles_to_add_ids:
        if rid not in current_role_ids:
            role = member.guild.get_role(rid)
            if role:
                to_add.append(role)
    
    if to_add:
        try:
            await member.add_roles(*to_add, reason="Open Solana Verification")
        except Exception as e:
            logger.error(f"Failed to add roles: {e}")

    # Remove
    to_remove = []
    for rid in roles_to_remove_ids:
        if rid in current_role_ids:
            role = member.guild.get_role(rid)
            if role:
                to_remove.append(role)
                
    if to_remove:
        try:
            await member.remove_roles(*to_remove, reason="Solana NFT Verification Sync")
        except Exception as e:
            logger.error(f"Failed to remove roles: {e}")
