import os
import requests
import logging
import jwt
import re
from pdf2image import convert_from_path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "your-fallback-secret-key-for-dev")
POPPLER_PATH = os.getenv("POPPLER_PATH") # Optional for Windows testing

def sign_state(whatsapp_id: str) -> str:
    """Signs the whatsapp_id into a JWT to prevent spoofing during OAuth"""
    payload = {
        "whatsapp_id": whatsapp_id,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_state(token: str) -> str:
    """Verifies the OAuth state JWT and returns the whatsapp_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("whatsapp_id")
    except jwt.ExpiredSignatureError:
        logger.error("OAuth state token expired")
        return None
    except jwt.InvalidTokenError:
        logger.error("Invalid OAuth state token")
        return None

def get_whatsapp_media_url(media_id: str):
    """Retrieves the direct download URL for a media ID from Meta's servers"""
    try:
        token = os.getenv("META_ACCESS_TOKEN")
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Meta Graph API Error (Media URL): {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json().get("url")
    except Exception as e:
        logger.error(f"Error fetching media URL: {e}")
        return None

def download_whatsapp_media(media_url: str, save_path: str):
    """Downloads media from the retrieved URL and saves it locally"""
    try:
        token = os.getenv("META_ACCESS_TOKEN")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(media_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Meta Download Error: {response.status_code}")
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return save_path
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None

def get_state_code(state_name: str) -> str:
    """Maps Indian State names to their 2-digit GST State Codes as per GSTR - State and code.md"""
    mapping = {
        "JAMMU AND KASHMIR": "01", "HIMACHAL PRADESH": "02", "PUNJAB": "03",
        "CHANDIGARH": "04", "UTTARAKHAND": "05", "HARYANA": "06",
        "DELHI": "07", "RAJASTHAN": "08", "UTTAR PRADESH": "09",
        "BIHAR": "10", "SIKKIM": "11", "ARUNACHAL PRADESH": "12",
        "NAGALAND": "13", "MANIPUR": "14", "MIZORAM": "15",
        "TRIPURA": "16", "MEGHALAYA": "17", "ASSAM": "18",
        "WEST BENGAL": "19", "JHARKHAND": "20", "ODISHA": "21",
        "CHHATTISGARH": "22", "MADHYA PRADESH": "23", "GUJARAT": "24",
        "DAMAN AND DIU": "25", "DAMAN & DIU": "25", 
        "DADRA AND NAGAR HAVELI": "26", "DADRA & NAGAR HAVELI": "26", 
        "MAHARASHTRA": "27", "ANDHRA PRADESH (OLD)": "28",
        "KARNATAKA": "29", "GOA": "30", "LAKSHADWEEP": "31",
        "KERALA": "32", "TAMIL NADU": "33", "PUDUCHERRY": "34",
        "ANDAMAN AND NICOBAR ISLANDS": "35", "ANDAMAN & NICOBAR ISLANDS": "35",
        "TELANGANA": "36", "ANDHRA PRADESH (NEW)": "37", "ANDHRA PRADESH": "37", 
        "LADAKH": "38"
    }
    normalized = str(state_name).strip().upper()
    
    if normalized.isdigit() and len(normalized) == 2:
        return normalized
    
    if normalized in mapping:
        return mapping[normalized]
    
    for name, code in mapping.items():
        if name in normalized or normalized in name:
            return code
            
    return "37"

def get_uqc_code(uqc_name: str) -> str:
    """Maps unit names to standard GST Unit Quantity Codes (UQC) as per GSTR-1 notes"""
    mapping = {
        "NUMBERS": "NOS", "PIECES": "PCS", "KILOGRAMS": "KGS",
        "GRAMS": "GMS", "QUINTAL": "QTL", "TONNES": "TON", "METRIC TON": "MTS",
        "METERS": "MTR", "LITRES": "LTR", "BOX": "BOX",
        "SETS": "SET", "DOZENS": "DOZ", "PACKS": "PAC",
        "BAGS": "BAG", "CARTONS": "CTN", "OTHERS": "OTH",
        "MILLILITRE": "MLT", "CANS": "CAN", "BOTTLES": "BTL", "DRUMS": "DRM",
        "SQUARE FEET": "SQF", "SQUARE METERS": "SQM", "YARDS": "YDS", "CENTIMETERS": "CMS",
        "BUNCHES": "BUN", "BUNDLES": "BDL", "TABLETS": "TBS", "TUBES": "TUB", "THOUSANDS": "THD",
        "KILO": "KGS", "METER": "MTR", "LITRE": "LTR"
    }
    normalized = uqc_name.strip().upper()
    
    if normalized in mapping.values():
        return normalized
        
    if normalized in mapping:
        return mapping[normalized]

    for name, code in mapping.items():
        if name in normalized or normalized in name:
            return code
            
    return "OTH"

def handle_google_error(recipient_id: str, error: Exception):
    """Notifies the user via WhatsApp if a Google API error occurs (Auth, Quota, etc)"""
    error_str = str(error).lower()
    
    # 1. Detect Authentication Errors (Revoked or Expired token)
    if "invalid_grant" in error_str or "auth" in error_str or "unauthorized" in error_str:
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
        base_url = redirect_uri.split('/auth/callback')[0]
        reauth_url = f"{base_url}/auth/google?whatsapp_id={recipient_id}"
        
        msg = (
            "⚠️ Help U has lost access to your Google Drive.\n\n"
            "This usually happens if you revoked permissions or your login expired. "
            "Please click here to re-authorize so I can continue bookkeeping:\n"
            f"{reauth_url}"
        )
        send_whatsapp_text(recipient_id, msg)
        return True

    # 2. Detect Storage Quota Errors
    elif "quotaexceeded" in error_str or "storage" in error_str:
        msg = (
            "🚨 Your Google Drive storage is full!\n\n"
            "I couldn't save your bill because there's no space left. "
            "Please clear some space in your Drive and try again."
        )
        send_whatsapp_text(recipient_id, msg)
        return True

    # 3. Handle other API errors
    else:
        logger.error(f"Unhandled Google API error for {recipient_id}: {error}")
        return False

def send_whatsapp_interactive(recipient_id: str, body: str, buttons: list, phone_number_id: str = None):
    """Sends an interactive message with buttons (max 3) or a list (up to 10) to the user"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        token = os.getenv("META_ACCESS_TOKEN")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        if len(buttons) <= 3:
            # Send standard Buttons (max 3)
            button_objects = []
            for i, btn_text in enumerate(buttons):
                button_objects.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i}",
                        "title": btn_text[:20] # Meta limit: 20 chars
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
        else:
            # Send List Message (up to 10)
            rows = []
            for i, btn_text in enumerate(buttons):
                rows.append({
                    "id": f"row_{i}",
                    "title": btn_text[:24], # Meta limit: 24 chars
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": body},
                    "action": {
                        "button": "Select Option",
                        "sections": [
                            {
                                "title": "Options",
                                "rows": rows
                            }
                        ]
                    }
                }
            }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending WhatsApp interactive message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None

def send_whatsapp_text(recipient_id: str, text: str, phone_number_id: str = None):
    """Sends a text message back to the user via WhatsApp Cloud API"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        token = os.getenv("META_ACCESS_TOKEN")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
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

def upload_whatsapp_media(file_path: str, phone_number_id: str = None):
    """Uploads a file to WhatsApp's media servers and returns the media ID"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        token = os.getenv("META_ACCESS_TOKEN")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/media"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Determine mime type (basic)
        # Note: Meta API does not support application/json for document uploads.
        # We use text/plain as a compatible fallback for JSON data.
        mime_type = "text/plain"
        if file_path.endswith(".pdf"): mime_type = "application/pdf"
        elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"): mime_type = "image/jpeg"
        
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, mime_type),
                "messaging_product": (None, "whatsapp"),
                "type": (None, mime_type)
            }
            
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            return response.json().get("id")
    except Exception as e:
        logger.error(f"Error uploading media to WhatsApp: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        return None

def send_whatsapp_document(recipient_id: str, media_id: str, filename: str, phone_number_id: str = None):
    """Sends a document (PDF, JSON, etc.) to a user via media ID"""
    try:
        phone_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID")
        token = os.getenv("META_ACCESS_TOKEN")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": filename
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending WhatsApp document: {e}")
        return None

def is_valid_gstin(gstin: str) -> bool:
    """Basic Regex validation for Indian GSTIN (15 characters)"""
    if not gstin:
        return True # Treat empty as valid (B2C)
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.strip().upper()))

def convert_image_to_pdf(image_path: str, pdf_path: str):
    """Converts an image file to a PDF file using Pillow"""
    try:
        from PIL import Image
        image = Image.open(image_path)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(pdf_path, "PDF", resolution=100.0)
        return pdf_path
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}")
        return None

def convert_pdf_to_image(pdf_path: str) -> str:
    """Converts the first page of a PDF to a JPG image for Vision analysis"""
    try:
        images = convert_from_path(
            pdf_path, 
            first_page=1, 
            last_page=1, 
            poppler_path=POPPLER_PATH
        )
        if images:
            image_path = pdf_path.replace(".pdf", ".jpg")
            images[0].save(image_path, "JPEG")
            return image_path
    except Exception as e:
        logger.error(f"Error converting PDF to image: {e}")
    return None

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text content from a PDF file using PyPDF2"""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return None
