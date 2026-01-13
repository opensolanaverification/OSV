# Open Solana Verification

An open-source, fully async Discord bot that verifies Solana NFT ownership and assigns tiered roles based on holdings using the Helius DAS API.

## Features

- **Wallet Verification**: Secure micro-SOL self-transfer verification (non-custodial).
- **Role Management**: Automatically assigns roles based on NFT counts in specific collections.
- **Support for Compressed NFTs**: Uses Helius DAS API to support all NFT standards on Solana.
- **Background Sync**: Periodically re-checks holdings and updates roles (default: every 15 mins).
- **Multi-Collection Support**: Track multiple collections with different tier structures.

## Technology Stack

- **Python 3.10+**
- **discord.py** (Slash Commands)
- **aiosqlite** (Async Database)
- **Helius DAS API** (Asset Indexing)
- **Solana.py / Solders** (Transaction Verification)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd <your-repo-dir>
    ```

2.  **Set up a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Create a `.env` file in the root directory:
    ```env
    DISCORD_TOKEN=your_discord_bot_token
    HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_api_key
    
    # Optional Configuration
    # GUILD_ID=123456789 (Syncs commands to specific guild)
    ```

## Usage

1.  **Run the Bot**:
    ```bash
    python main.py
    ```

2.  **Discord Commands**:

    **User Commands**:
    - `/connect_wallet <address>`: Start the wallet verification process.
    - `/my_wallet`: View your linked Solana wallet or manage your connection.

    **Admin Commands**:
    - `/add_collection <address> <name>`: Start tracking a collection.
    - `/set_tier <collection_address> <min_nfts> <role>`: Assign a role for holding N NFTs.

## Maintenance

### Syncing Commands
Slash commands (the ones starting with `/`) do not sync automatically on startup to improve performance and avoid duplicates. Admins must manually sync them when changes are made:

- **Command**: `!sync`
- **Permissions**: Required **Bot Owner** permissions.
- **Sync Speed**: If `GUILD_ID` is set in `.env`, the sync is **instant**. Global sync (no `GUILD_ID`) can take up to 1 hour to propagate.

## Architecture

- `src/bot.py`: Main Discord bot instance and command handlers.
- `src/role_engine.py`: Logic for determining user roles.
- `src/helius_client.py`: Async client for Helius Digital Asset Standard (DAS) API.
- `src/solana_verifier.py`: Verification of on-chain self-transfer transactions.
- `src/tasks.py`: Background tasks for role synchronization.

## License

MIT
