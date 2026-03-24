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
        If the message is not a transaction (e.g., "Hi", "How are you?"), set "is_transaction" to false and "is_greeting" to true.

        Extraction Rules:
        1. Intent Detection: 
           - Set "is_transaction" to true if the message describes a sale, purchase, expense, payment (rent, bill, repair), or bill.
           - Set "is_transaction" to false if it's a greeting, casual chat, or irrelevant text.
           - Set "is_greeting" to true if the user is saying hi/hello.
           - Set "is_correction" to true if the user is correcting a previous entry (e.g., "Amount is 500").
           - Set "is_query" to true if the user is asking about their ledger data (e.g., "How much did I sell to Apollo?").
           - Set "is_consultant_query" to true if the user is asking for business advice, analysis, or performance checks (e.g., "Analyze my month", "Should I buy more from Apollo?").
        2. Identify GSTINs: Find both 'Supplier GSTIN' and 'Recipient GSTIN'.
        3. Items Extraction: ALWAYS extract items into the "items" list. If there are multiple products/services, list each one separately with its respective HSN, rate, quantity, and taxes.
        4. Payment Specifics: If it's a "Payment", identify if it's "Single" or "Recurring" and the "frequency" (Monthly/Yearly).
        5. Tax Split: Calculate or extract CGST, SGST, and IGST for each item. If the state of the supplier matches the user, use CGST/SGST. If different, use IGST.
        5. HSN Codes: Extract the 4 or 8-digit HSN code for each item. If missing, suggest the most likely 4-digit code based on the item description.
        6. Invoice Type: 
           - Set to B2B if a Recipient GSTIN is present.
           - Set to B2CS (Small) if no Recipient GSTIN is found and total is below 2.5 Lakh.
        7. GSTR-1 Specifics:
           - Extract 'Place Of Supply' (State name or 2-digit GST state code).
           - Identify 'Reverse Charge' (Set to 'Y' or 'N').
           - UQC: Use standard GST codes (NOS, KGS, PCS, BOX, LTR, MTR, SET, OTH).
           - Quantity: Extract the numeric quantity.
           - HSN Description: A brief 2-5 word description of the item.

        Required JSON Output Format:
        {
          "is_transaction": boolean,
          "is_greeting": boolean,
          "is_correction": boolean,
          "is_query": boolean,
          "is_consultant_query": boolean,
          "query_details": {
            "entity": "string (e.g. Apollo Pharm)",
            "metric": "total_sales / total_purchases / balance",
            "time_period": "this_month / last_month / all_time"
          },
          "corrections": {
            "field": "value" 
          },
          "transaction_type": "Purchase/Sale/Expense/Payment",
          "payment_details": {
            "type": "Single/Recurring",
            "frequency": "Monthly/Yearly/N/A"
          },
          "invoice_no": "string",
          "date": "DD-MM-YYYY",
          "vendor_name": "string",
          "vendor_gstin": "string",
          "recipient_gstin": "string",
          "place_of_supply": "string (State name or 2-digit code)",
          "reverse_charge": "Y/N",
          "items": [
            {
              "hsn_code": "string",
              "hsn_description": "string",
              "uqc": "string",
              "quantity": 0.00,
              "gst_rate": 0,
              "taxable_value": 0.00,
              "cgst": 0.00,
              "sgst": 0.00,
              "igst": 0.00,
              "total_amount": 0.00
            }
          ],
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
