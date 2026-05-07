import os
import logging
import requests
import asyncio
from datetime import datetime
from abc import ABC, abstractmethod
from src.firestore_service import GSTCache, FirestoreSession

logger = logging.getLogger(__name__)

class GSTProvider(ABC):
    """Abstract base class for GST data providers"""
    @abstractmethod
    async def lookup_hsn(self, code: str) -> dict:
        pass

    @abstractmethod
    async def search_hsn(self, query: str) -> list:
        pass

class FastGSTProvider(GSTProvider):
    """Implementation for FastGST.in API"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.taxlookup.fastgst.in"

    async def lookup_hsn(self, code: str) -> dict:
        """Lookup GST rates and description for a specific HSN code"""
        try:
            # First get basic info (description)
            info_url = f"{self.base_url}/search/hsn/{code}"
            # Then get tax info
            tax_url = f"{self.base_url}/search/hsn/{code}/taxes"
            
            headers = {"x-api-key": self.api_key}
            loop = asyncio.get_event_loop()
            
            # Fetch both in parallel
            async def fetch(url):
                return await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))

            info_res, tax_res = await asyncio.gather(fetch(info_url), fetch(tax_url))
            
            if info_res.status_code == 200 and tax_res.status_code == 200:
                info_data = info_res.json().get("data", {})
                tax_data = tax_res.json().get("data", {})
                
                return {
                    "hsn_code": code,
                    "description": info_data.get("description", "Unknown Item"),
                    "gst_rate": tax_data.get("gst_rate", 0),
                    "uqc": "PCS", # Default
                    "raw": {"info": info_data, "tax": tax_data}
                }
            
            logger.error(f"FastGST lookup failed: Info={info_res.status_code}, Tax={tax_res.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error in FastGST lookup_hsn: {e}")
            return None

    async def search_hsn(self, query: str) -> list:
        """Search HSN codes by description"""
        try:
            url = f"{self.base_url}/search/hsn"
            params = {"query": query}
            headers = {"x-api-key": self.api_key}
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=headers, params=params, timeout=10)
            )
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                results = []
                for group in data:
                    for m in group.get("matches", []):
                        results.append({
                            "hsn_code": m.get("hsn_code"),
                            "description": m.get("description"),
                            "gst_rate": 18, # Search doesn't return rate, default to 18 or caller must lookup
                            "uqc": "PCS"
                        })
                return results[:10]
            return []
        except Exception as e:
            logger.error(f"Error in FastGST search_hsn: {e}")
            return []

class GSTLookupService:
    """Orchestrator for GST lookups with caching support"""
    def __init__(self):
        api_key = os.getenv("GST_API_KEY")
        # Easy to swap provider here based on env or config
        self.provider = FastGSTProvider(api_key) if api_key else None
        self.db = FirestoreSession()

    async def get_hsn_details(self, code: str) -> dict:
        if not code: return None
        
        # 1. Check Cache
        query_key = f"hsn_{code}"
        cached = self.db.query(GSTCache).filter(GSTCache.query_key == query_key).first()
        if cached:
            logger.info(f"GST Service: Cache hit for {query_key}")
            return cached.result_data

        # 2. Call Provider
        if not self.provider:
            logger.warning("No GST provider configured")
            return None
            
        logger.info(f"GST Service: Calling provider for {code}")
        result = await self.provider.lookup_hsn(code)
        
        # 3. Save to Cache if result found
        if result:
            new_cache = GSTCache(
                query_key=query_key,
                result_data=result,
                provider="fastgst",
                updated_at=datetime.utcnow()
            )
            self.db.add(new_cache)
            self.db.commit()
            
        return result

    async def search_products(self, query: str) -> list:
        """Search for products/HSN codes by keywords"""
        if not query: return []
        
        # We don't necessarily cache searches as they are dynamic, 
        # but we could cache exact query matches if needed.
        query_key = f"search_{query.lower().strip()}"
        cached = self.db.query(GSTCache).filter(GSTCache.query_key == query_key).first()
        if cached:
            return cached.result_data

        if not self.provider: return []
        
        results = await self.provider.search_hsn(query)
        if results:
            new_cache = GSTCache(
                query_key=query_key,
                result_data=results,
                provider="fastgst",
                updated_at=datetime.utcnow()
            )
            self.db.add(new_cache)
            self.db.commit()
            
        return results
