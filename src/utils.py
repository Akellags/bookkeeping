import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

def get_whatsapp_media_url(media_id: str):
    """Retrieves the direct download URL for a media ID from Meta's servers"""
    try:
        url = f"https://graph.facebook.com/v17.0/{media_id}"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("url")
    except Exception as e:
        logger.error(f"Error fetching media URL: {e}")
        return None

def download_whatsapp_media(media_url: str, save_path: str):
    """Downloads media from the retrieved URL and saves it locally"""
    try:
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return save_path
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None

def get_state_code(state_name: str) -> str:
    """Maps Indian State names to their 2-digit GST State Codes"""
    mapping = {
        "JAMMU AND KASHMIR": "01", "HIMACHAL PRADESH": "02", "PUNJAB": "03",
        "CHANDIGARH": "04", "UTTARAKHAND": "05", "HARYANA": "06",
        "DELHI": "07", "RAJASTHAN": "08", "UTTAR PRADESH": "09",
        "BIHAR": "10", "SIKKIM": "11", "ARUNACHAL PRADESH": "12",
        "NAGALAND": "13", "MANIPUR": "14", "MIZORAM": "15",
        "TRIPURA": "16", "MEGHALAYA": "17", "ASSAM": "18",
        "WEST BENGAL": "19", "JHARKHAND": "20", "ODISHA": "21",
        "CHHATTISGARH": "22", "MADHYA PRADESH": "23", "GUJARAT": "24",
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "26", "MAHARASHTRA": "27",
        "KARNATAKA": "29", "GOA": "30", "LAKSHADWEEP": "31",
        "KERALA": "32", "TAMIL NADU": "33", "PUDUCHERRY": "34",
        "ANDAMAN AND NICOBAR ISLANDS": "35", "TELANGANA": "36",
        "ANDHRA PRADESH": "37", "LADAKH": "38"
    }
    # Normalize input: uppercase and remove extra spaces
    normalized = state_name.strip().upper()
    
    # Check for direct match
    if normalized in mapping:
        return mapping[normalized]
    
    # Simple fuzzy search for common variations
    for name, code in mapping.items():
        if name in normalized or normalized in name:
            return code
            
    return "37" # Default to user state (Andhra Pradesh) if unknown

def get_uqc_code(uqc_name: str) -> str:
    """Maps unit names to standard GST Unit Quantity Codes (UQC)"""
    mapping = {
        "NUMBERS": "NOS", "PIECES": "PCS", "KILOGRAMS": "KGS",
        "GRAMS": "GMS", "QUINTAL": "QTL", "TONNES": "TON",
        "METERS": "MTR", "LITRES": "LTR", "BOX": "BOX",
        "SETS": "SET", "DOZENS": "DOZ", "PACKS": "PAC",
        "BAGS": "BAG", "CARTONS": "CTN", "OTHERS": "OTH"
    }
    normalized = uqc_name.strip().upper()
    
    # Direct match in values (e.g., already "NOS")
    if normalized in mapping.values():
        return normalized
        
    # Check mapping
    for name, code in mapping.items():
        if name in normalized or normalized in name:
            return code
            
    return "OTH"

def send_whatsapp_interactive(recipient_id: str, body: str, buttons: list, phone_number_id: str = None):
    """Sends an interactive message with buttons to the user via WhatsApp Cloud API"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        button_objects = []
        for i, btn_text in enumerate(buttons):
            button_objects.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_{i}",
                    "title": btn_text
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": button_objects}
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending WhatsApp interactive message: {e}")
        return None

def send_whatsapp_text(recipient_id: str, text: str, phone_number_id: str = None):
    """Sends a text message back to the user via WhatsApp Cloud API"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": text}
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return None
