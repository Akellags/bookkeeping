import requests
import time

def test_connectivity():
    url = "https://sheets.googleapis.com/$discovery/rest?version=v4"
    print(f"Testing connectivity to {url}...")
    start = time.time()
    try:
        response = requests.get(url, timeout=30)
        duration = time.time() - start
        print(f"SUCCESS: Received response in {duration:.2f}s (Status: {response.status_code})")
    except Exception as e:
        duration = time.time() - start
        print(f"FAILED after {duration:.2f}s: {e}")

if __name__ == "__main__":
    test_connectivity()
