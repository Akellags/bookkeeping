import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

from src.bot.templates import TemplateHandler

async def test_templates():
    handler = TemplateHandler()
    
    # Mock GST Service for discovery tests
    handler.gst_service = AsyncMock()
    handler.gst_service.get_hsn_details.return_value = {
        "hsn_code": "8471",
        "description": "Computers",
        "gst_rate": 18,
        "uqc": "NOS"
    }
    handler.gst_service.search_products.return_value = [{
        "hsn_code": "8471",
        "description": "Keyboard",
        "gst_rate": 12,
        "uqc": "PCS"
    }]

    # 1. Single Line Sale (No GSTIN) - Amount is now treated as Taxable Value
    # User provided 18% in the string, which should override Discovery's 12%
    sale_text = "S | Apollo Pharm | 1200 | 18 | Medicines | 04-05-2026 | INV-101 | 27 | PCS"
    print(f"Testing Single Line Sale: {sale_text}")
    res = await handler.parse(sale_text)
    print(json.dumps(res, indent=2))
    assert res['transaction_type'] == "Sale"
    # 1200 * 1.18 = 1416.0 (User provided 18 takes priority over Discovery 12)
    assert res['total_amount'] == 1416.0
    
    # 2. Multi-Line Sale with GSTIN (User Example)
    sale_text_multi = """S | Sridhar | 36AAACY6329B1ZH | 01-05-2026 | INV-101 | TS
    Logitech Keyboard | 2 | 1200 | 18
    Logitech Mouse | 5 | 600 | 12"""
    print(f"\nTesting Multi-Line Sale: {sale_text_multi}")
    res = await handler.parse(sale_text_multi)
    assert res['recipient_gstin'] == "36AAACY6329B1ZH"
    assert res['total_amount'] == 6192.0

    # 3. Discovery Test: Unknown product (Numeric HSN)
    discovery_text = "S | New Client | 5000 | 18 | 8471"
    print(f"\nTesting Discovery (Numeric HSN): {discovery_text}")
    res = await handler.parse(discovery_text)
    print(json.dumps(res, indent=2))
    assert res['items'][0]['hsn_code'] == "8471"
    assert res['items'][0]['hsn_description'] == "Computers"

    # 4. Discovery Test: Unknown product (Keyword Search)
    keyword_text = "S | New Client | 3000 | 12 | Wireless Mouse"
    print(f"\nTesting Discovery (Keyword Search): {keyword_text}")
    res = await handler.parse(keyword_text)
    print(json.dumps(res, indent=2))
    assert res['items'][0]['hsn_code'] == "8471"
    # Note: Search keeps the original user description but uses found HSN/Rate
    assert res['items'][0]['gst_rate'] == 12

    print("\n[SUCCESS] All template tests (including discovery) passed!")

if __name__ == "__main__":
    asyncio.run(test_templates())
