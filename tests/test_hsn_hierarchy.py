import requests
import json

def test_hsn_hierarchy():
    api_key = "FGST_TEST_1TZZ5SBX86JA6ACH8VCUI3YY"
    base_url = "https://api.taxlookup.fastgst.in"
    
    # Testing if looking up a 4-digit code returns children/sub-categories
    code = "8517"
    url = f"{base_url}/search/hsn/{code}"
    headers = {"x-api-key": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status for {code}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Look for sub-categories in the response
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_hsn_hierarchy()
