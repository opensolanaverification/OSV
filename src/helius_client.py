import aiohttp
import asyncio
import logging
from .config import HELIUS_RPC_URL, HELIUS_RATE_LIMIT_DELAY

logger = logging.getLogger(__name__)

class HeliusClient:
    def __init__(self):
        self.url = HELIUS_RPC_URL

    async def get_assets_by_group(self, collection_address: str, page: int = 1, limit: int = 1000):
        """
        Fetches assets for a specific collection (group).
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getAssetsByGroup",
            "params": {
                "groupKey": "collection",
                "groupValue": collection_address,
                "page": page,
                "limit": limit
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Helius API error: {response.status} - {await response.text()}")
                        return []
                    
                    data = await response.json()
                    if "result" in data:
                         return data["result"].get("items", [])
                    else:
                        logger.error(f"Helius API error: {data}")
                        return []
        except Exception as e:
            logger.exception(f"Exception calling Helius API: {e}")
            return []

    async def get_assets_by_owner(self, owner_address: str, page: int = 1, limit: int = 1000):
         payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getAssetsByOwner",
            "params": {
                "ownerAddress": owner_address,
                "page": page,
                "limit": limit,
                 "displayOptions": {
                    "showUnverifiedCollections": False,
                    "showCollectionMetadata": True
                }
            }
        }
         try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload) as response:
                    if response.status != 200:
                         logger.error(f"Helius API error: {response.status} - {await response.text()}")
                         return []
                    
                    data = await response.json()
                    if "result" in data:
                         return data["result"].get("items", [])
                    else:
                         logger.error(f"Helius API error: {data}")
                         return []
         except Exception as e:
            logger.exception(f"Exception calling Helius API: {e}")
            return []

    async def get_all_assets_by_owner(self, owner_address: str):
        """
        Fetches all assets for a given owner, handling pagination.
        """
        all_assets = []
        page = 1
        limit = 1000
        
        while True:
            assets = await self.get_assets_by_owner(owner_address, page, limit)
            if not assets:
                break
            
            all_assets.extend(assets)
            
            if len(assets) < limit:
                break
                
            page += 1
            await asyncio.sleep(HELIUS_RATE_LIMIT_DELAY) # Rate limiting
            
        return all_assets

