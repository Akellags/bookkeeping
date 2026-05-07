import sys
import os
import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

from src.gst_service import GSTLookupService, FastGSTProvider

async def test_gst_service_logic():
    print("Running GST Service Logic Tests...")
    
    # Initialize service
    service = GSTLookupService()
    
    # Mock the provider to avoid real API calls for logic test
    mock_provider = AsyncMock(spec=FastGSTProvider)
    mock_provider.lookup_hsn.return_value = {
        "hsn_code": "8471",
        "description": "Automatic data processing machines (Computers)",
        "gst_rate": 18,
        "uqc": "NOS"
    }
    service.provider = mock_provider
    mock_provider.lookup_hsn.reset_mock()
    
    # 1. Test First Lookup (Should call provider)
    # We use a unique code to avoid existing real cache interference
    test_code = f"TEST_{int(datetime.now().timestamp())}"
    mock_provider.lookup_hsn.return_value["hsn_code"] = test_code

    print(f"\n[Test 1] First lookup for HSN {test_code}...")
    result = await service.get_hsn_details(test_code)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["hsn_code"] == test_code
    assert mock_provider.lookup_hsn.called
    
    # 2. Test Second Lookup (Should hit cache)
    print(f"\n[Test 2] Second lookup for HSN {test_code} (should be cached)...")
    mock_provider.lookup_hsn.reset_mock()
    
    result2 = await service.get_hsn_details(test_code)
    assert result2["hsn_code"] == test_code
    assert not mock_provider.lookup_hsn.called, "Provider should NOT be called for cached data"
    
    # Note: In our current FirestoreSession mock, it might not persist 
    # perfectly across calls if not careful, but the logic in service.py is what we test.
    # If using the real FirestoreSession, it will persist to Firebase.
    
    print("\n[SUCCESS] GST Service logic tests passed!")

async def test_real_api_search():
    """Optional: Test with real API if key is present"""
    api_key = os.getenv("GST_API_KEY")
    if not api_key or "TEST" in api_key:
        print("\nSkipping real API search test (Key is Test/Missing)")
        return

    print(f"\n[Test 3] Testing real API search for 'Keyboard'...")
    service = GSTLookupService()
    results = await service.search_products("Keyboard")
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f" - {r['hsn_code']}: {r['description']} ({r['gst_rate']}%)")

if __name__ == "__main__":
    asyncio.run(test_gst_service_logic())
    asyncio.run(test_real_api_search())
