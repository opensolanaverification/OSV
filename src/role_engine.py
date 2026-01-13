import logging
from typing import Set, Tuple, Optional
from .db import Database
from .helius_client import HeliusClient

logger = logging.getLogger(__name__)

class RoleEngine:
    def __init__(self, db: Database, helius: HeliusClient):
        self.db = db
        self.helius = helius

    async def get_global_holdings(self) -> dict:
        """
        Fetches all assets for all tracked collections and builds a global holdings map.
        Returns: {wallet_address: {collection_address: count}}
        """
        collections = await self.db.get_all_collections()
        global_holdings = {} # wallet_address -> {collection_address: count}
        
        for coll_row in collections:
            coll_addr = coll_row[0]
            logger.info(f"Fetching all assets for collection: {coll_addr}")
            assets = await self.helius.get_all_assets_by_group(coll_addr)
            
            for asset in assets:
                owner = asset.get("ownership", {}).get("owner")
                if not owner:
                    continue
                
                if owner not in global_holdings:
                    global_holdings[owner] = {}
                
                global_holdings[owner][coll_addr] = global_holdings[owner].get(coll_addr, 0) + 1
                
        return global_holdings

    async def calculate_roles(self, wallet_address: Optional[str]) -> Tuple[Set[int], Set[int]]:
        """
        Calculates which roles should be added and removed for a specific wallet.
        Used for instant verification / !test command.
        """
        collections = await self.db.get_all_collections()
        if not collections:
            return set(), set()
        
        if wallet_address:
            assets = await self.helius.get_all_assets_by_owner(wallet_address)
        else:
            assets = []
        
        holdings = {}
        for asset in assets:
            grouping = asset.get("grouping", [])
            for group in grouping:
                if group.get("group_key") == "collection":
                    addr = group.get("group_value")
                    holdings[addr] = holdings.get(addr, 0) + 1
        
        return await self.calculate_roles_from_holdings(holdings, collections)

    async def calculate_roles_from_holdings(self, user_holdings: dict, all_collections: list) -> Tuple[Set[int], Set[int]]:
        """
        Core logic to match holdings against tiers.
        user_holdings: {collection_address: count}
        all_collections: list of collection rows from DB
        """
        roles_to_add = set()
        roles_to_keep = set()
        all_managed_roles = set()

        for coll_row in all_collections:
            coll_addr = coll_row[0]
            tiers = await self.db.get_tiers(coll_addr)
            
            user_count = user_holdings.get(coll_addr, 0)
            
            found_highest = False
            for tier in tiers:
                min_amount = tier[2]
                role_id = tier[3]
                all_managed_roles.add(role_id)
                
                if not found_highest and user_count >= min_amount:
                    roles_to_add.add(role_id)
                    roles_to_keep.add(role_id)
                    found_highest = True
                
        roles_to_remove = all_managed_roles - roles_to_keep
        return roles_to_add, roles_to_remove
