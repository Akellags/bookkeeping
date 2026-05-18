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

    @abstractmethod
    async def search_sac(self, query: str) -> list:
        pass

class FastGSTProvider(GSTProvider):
    """Implementation for FastGST.in API"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.taxlookup.fastgst.in"

    async def lookup_hsn(self, code: str) -> dict:
        """Lookup GST rates and description for a specific HSN or SAC code"""
        try:
            # Detect type: HSN or SAC
            ctype = "sac" if str(code).startswith("99") else "hsn"
            
            # First get basic info (description)
            info_url = f"{self.base_url}/search/{ctype}/{code}"
            # Then get tax info
            tax_url = f"{self.base_url}/search/{ctype}/{code}/taxes"
            
            headers = {"x-api-key": self.api_key}
            loop = asyncio.get_event_loop()
            
            # Fetch both in parallel
            async def fetch(url):
                return await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))

            info_res, tax_res = await asyncio.gather(fetch(info_url), fetch(tax_url))
            
            if info_res.status_code == 200 and tax_res.status_code == 200:
                info_data = info_res.json().get("data", {})
                tax_data = tax_res.json().get("data", {})
                
                # FastGST returns 'sac_code' for SAC and 'hsn_code' for HSN
                returned_code = info_data.get("hsn_code") or info_data.get("sac_code") or code
                
                return {
                    "hsn_code": returned_code,
                    "description": info_data.get("description", "Unknown Item"),
                    "gst_rate": tax_data.get("gst_rate", 0),
                    "uqc": "OTH" if ctype == "sac" else "PCS", # Default OTH for services
                    "type": ctype.upper(),
                    "raw": {"info": info_data, "tax": tax_data}
                }
            
            logger.error(f"FastGST lookup failed for {ctype} {code}: Info={info_res.status_code}, Tax={tax_res.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error in FastGST lookup_hsn: {e}")
            return None

    async def search_sac(self, query: str) -> list:
        """Search SAC codes by description"""
        try:
            url = f"{self.base_url}/search/sac"
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
                            "hsn_code": m.get("sac_code"), # Use common field name for FE
                            "description": m.get("description"),
                            "gst_rate": 18, 
                            "is_parent": False, # SAC is usually specific
                            "type": "SAC"
                        })
                return results
            return []
        except Exception as e:
            logger.error(f"Error in FastGST search_sac: {e}")
            return []

    async def search_hsn(self, query: str) -> list:
        """Search HSN codes by description or code with recursive drill-down"""
        try:
            import re
            # 1. Detect if query is an HSN code prefix (e.g., "8517")
            is_code_search = query.isdigit() and len(query) >= 2
            
            clean_query = re.sub(r'[\(\)\[\]]', ' ', query).strip()
            
            async def perform_search(q):
                url = f"{self.base_url}/search/hsn"
                # If it's a code search, we use the query directly, otherwise search by description
                params = {"query": q}
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
                                "gst_rate": 18, # Default for search
                                "is_parent": len(m.get("hsn_code", "")) < 8,
                                "type": "HSN",
                                "uqc": "PCS"
                            })
                    return results
                else:
                    logger.error(f"FastGST search failed for '{q}': {response.status_code}")
                    return []

            # 2. Execute Search
            results = await perform_search(clean_query)
            
            # 3. Fallbacks for Keyword Search
            if not results and not is_code_search:
                words = clean_query.split()
                # Fallback A: First 2 words
                if len(words) > 2:
                    fallback_query = " ".join(words[:2])
                    results = await perform_search(fallback_query)
                
                # Fallback B: Product Category (usually last or 2nd word)
                if not results and len(words) >= 2:
                    results = await perform_search(words[1])
                    if not results and len(words) > 2:
                        results = await perform_search(words[-1])
            
            # 4. Smart Ranking & Deduplication
            if results:
                # Deduplicate by HSN Code
                seen_hsn = set()
                unique_results = []
                for r in results:
                    if r['hsn_code'] not in seen_hsn:
                        unique_results.append(r)
                        seen_hsn.add(r['hsn_code'])
                
                # Rank: Items where query matches description exactly or starts with it
                q_lower = clean_query.lower()
                def rank_score(item):
                    desc = item['description'].lower()
                    # Priority 1: Exact match on HSN code (if it was a code search)
                    if is_code_search and item['hsn_code'] == q_lower: return -1
                    # Priority 2: Description starts with query (e.g. "Mobile phones...")
                    if desc.startswith(q_lower): return 0
                    # Priority 3: Contains as word
                    if f" {q_lower} " in f" {desc} ": return 1
                    # Priority 4: Electronics priority (Chapter 84/85) for tech terms
                    tech_terms = ['mobile', 'phone', 'laptop', 'computer', 'electronic', 'tablet']
                    is_tech_query = any(t in q_lower for t in tech_terms)
                    is_tech_hsn = item['hsn_code'].startswith(('84', '85'))
                    if is_tech_query and is_tech_hsn: return 2
                    # Priority 5: Contains anywhere
                    if q_lower in desc: return 3
                    return 4
                
                unique_results.sort(key=rank_score)
                return unique_results[:20]
            
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
        
        # 1. Detect type for accurate cache key
        ctype = "sac" if str(code).startswith("99") else "hsn"
        query_key = f"{ctype}_{code}"
        
        cached = self.db.query(GSTCache).filter(GSTCache.query_key == query_key).first()
        if cached:
            logger.info(f"GST Service: Cache hit for {query_key}")
            return cached.result_data

        # 2. Call Provider
        if not self.provider:
            logger.warning("No GST provider configured")
            return None
            
        logger.info(f"GST Service: Calling provider for {ctype} {code}")
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
        """Search for products/HSN/SAC codes by keywords"""
        if not query: return []
        
        query_key = f"search_{query.lower().strip()}"
        cached = self.db.query(GSTCache).filter(GSTCache.query_key == query_key).first()
        if cached:
            return cached.result_data

        if not self.provider: return []
        
        # 1. Try HSN Search First
        results = await self.provider.search_hsn(query)
        
        # 2. Try SAC Search if HSN yields low results or no relevant results
        if len(results) < 3:
            sac_results = await self.provider.search_sac(query)
            results.extend(sac_results)
            
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
