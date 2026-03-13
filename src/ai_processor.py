import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.system_prompt = """
        Role: You are a specialist Indian GST Compliance Accountant. 
        Task: Analyze the provided image (bill) or text/voice transcript (sale) and extract data into a strict JSON format.

        Extraction Rules:
        1. Identify GSTINs: Find both 'Supplier GSTIN' and 'Recipient GSTIN'.
        2. Tax Split: Calculate or extract CGST, SGST, and IGST separately. If the state of the supplier matches the user, use CGST/SGST. If different, use IGST.
        3. HSN Codes: Extract the 4 or 8-digit HSN code. If missing, suggest the most likely 4-digit code based on the item description.
        4. Invoice Type: 
           - Set to B2B if a Recipient GSTIN is present.
           - Set to B2CS (Small) if no Recipient GSTIN is found and total is below 2.5 Lakh.
        5. GSTR-1 Specifics:
           - Extract 'Place Of Supply' (State name or 2-digit GST state code).
           - Identify 'Reverse Charge' (Set to 'Y' or 'N').
           - UQC: Use standard GST codes (NOS, KGS, PCS, BOX, LTR, MTR, SET, OTH).
           - Quantity: Extract the numeric quantity.
           - HSN Description: A brief 2-5 word description of the item.

        Required JSON Output Format:
        {
          "transaction_type": "Purchase/Sale",
          "invoice_no": "string",
          "date": "DD-MM-YYYY",
          "vendor_name": "string",
          "vendor_gstin": "string",
          "recipient_gstin": "string",
          "place_of_supply": "string",
          "reverse_charge": "Y/N",
          "hsn_code": "string",
          "hsn_description": "string",
          "uqc": "string",
          "quantity": 0.00,
          "taxable_value": 0.00,
          "gst_rate": 0,
          "cgst": 0.00,
          "sgst": 0.00,
          "igst": 0.00,
          "total_amount": 0.00
        }
        """

    def process_purchase_image(self, image_url: str):
        """Processes a bill image using GPT-4o-mini Vision API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract GST data from this bill image."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error processing purchase image: {e}")
            return None

    def process_sales_text(self, text: str):
        """Processes sales voice transcript or text message"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Extract GST data from this sales record: {text}"}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error processing sales text: {e}")
            return None
