import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_gst_rates():
    url = "https://cbic-gst.gov.in/gst-goods-services-rates.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch page: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table')
    
    print(f"Found {len(tables)} tables. Processing...")
    
    rates_data = []
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]: # Skip header
            cols = row.find_all('td')
            if len(cols) >= 5:
                # Column structure based on WebFetch observation:
                # 0: Schedule/S.No, 1: Chapter/Heading, 2: Description, 3: CGST, 4: SGST, 5: IGST
                
                # Note: Some tables might have different structures, but we'll try to adapt
                chapter_info = cols[1].get_text(strip=True)
                description = cols[2].get_text(strip=True)
                cgst = cols[3].get_text(strip=True)
                sgst = cols[4].get_text(strip=True)
                igst = cols[5].get_text(strip=True) if len(cols) > 5 else ""
                
                # Basic cleaning
                rates_data.append({
                    "hsn_heading": chapter_info,
                    "description": description,
                    "cgst": cgst,
                    "sgst": sgst,
                    "igst": igst
                })

    output_path = r'c:\Users\ALIENWARE\Projects\helpU\bookkeeper\docs\gst_rates.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rates_data, f, indent=2)
    
    print(f"Successfully scraped {len(rates_data)} rate entries to {output_path}")

if __name__ == "__main__":
    scrape_gst_rates()
