import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

# Helius Configuration
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Solana Configuration
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", HELIUS_RPC_URL)

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# Verification Configuration
VERIFICATION_AMOUNT_MIN = 0.000001
VERIFICATION_AMOUNT_MAX = 0.000099
VERIFICATION_EXPIRY_SECONDS = 300  # 5 minutes

# Rate Limits
HELIUS_RATE_LIMIT_DELAY = 1.1  # Seconds between requests (per specs)
