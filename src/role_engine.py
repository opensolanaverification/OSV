import logging
import asyncio
from typing import List, Set, Tuple, Optional
from .db import Database
from .helius_client import HeliusClient

logger = logging.getLogger(__name__)

class RoleEngine:
    def __init__(self, db: Database, helius: HeliusClient):
        self.db = db
        self.helius = helius

    async def calculate_roles(self, wallet_address: Optional[str]) -> Tuple[Set[int], Set[int]]:
        """
        Calculates which roles should be added and removed for a specific wallet.
        Returns: (roles_to_add, roles_to_remove)
        """
        # 1. Fetch all tracked collections
        collections = await self.db.get_all_collections()
        if not collections:
            return set(), set()
        
        # 2. Fetch all assets for the user
        if wallet_address:
            assets = await self.helius.get_all_assets_by_owner(wallet_address)
        else:
            assets = []
        
        # 3. Group assets by collection
        holdings = {} # collection_address -> count
        for asset in assets:
            grouping = asset.get("grouping", [])
            for group in grouping:
                if group.get("group_key") == "collection":
                    coll_addr = group.get("group_value")
                    holdings[coll_addr] = holdings.get(coll_addr, 0) + 1
        
        # 4. Determine roles per collection
        roles_to_add = set()
        roles_to_keep = set() # Roles that the user qualifies for
        all_tracked_roles = set() # All roles managed by the bot

        for collection_row in collections:
            collection_address = collection_row[0]
            tiers = await self.db.get_tiers(collection_address) # Ordered by min_amount DESC
            
            user_count = holdings.get(collection_address, 0)
            
            # Find the highest tier the user qualifies for (highest only)
            found_highest = False
            for tier in tiers:
                # tier: (id, collection, min_amount, role_id)
                min_amount = tier[2]
                role_id = tier[3]
                all_tracked_roles.add(role_id)
                
                if not found_highest and user_count >= min_amount:
                    roles_to_add.add(role_id)
                    roles_to_keep.add(role_id)
                    found_highest = True
                
        # 5. Roles to remove = All tracked roles - roles to keep
        roles_to_remove = all_tracked_roles - roles_to_keep
        
        return roles_to_add, roles_to_remove
