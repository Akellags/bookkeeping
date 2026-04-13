import os
import json
import logging
import httpx
import base64
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from src.extraction.base import BaseExtractor
from src.extraction.schemas import ExtractionRequest, ExtractionResult, CanonicalTransaction

logger = logging.getLogger(__name__)

class OpenAIExtractor(BaseExtractor):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()
            
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=httpx.AsyncClient(timeout=120.0)
        )
        self.model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
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
          "recipient_name": "string",
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Processes a file and returns extracted transaction data in canonical format."""
        
        # Determine extraction type based on mime type
        if req.mime_type.startswith("image/"):
            return await self._extract_from_image(req)
        elif req.mime_type == "application/pdf":
            # For OpenAI, we convert PDF to image for vision or use text if vision fails
            # Currently we convert in the caller, but let's assume we get image-like data if it's already converted
            return await self._extract_from_image(req)
        else:
            # Fallback to text extraction for other types
            return await self._extract_from_text(req)

    async def _extract_from_image(self, req: ExtractionRequest) -> ExtractionResult:
        with open(req.media_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode('utf-8')
        
        image_data_uri = f"data:{req.mime_type};base64,{encoded_image}"
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract GST data from this bill image."},
                        {"type": "image_url", "image_url": {"url": image_data_uri}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        raw_json = json.loads(response.choices[0].message.content)
        canonical = CanonicalTransaction(**raw_json)
        
        return ExtractionResult(
            extraction_provider="openai",
            provider_model=self.model,
            canonical_data=canonical
        )

    async def _extract_from_text(self, req: ExtractionRequest) -> ExtractionResult:
        # If it's a text file, read content
        with open(req.media_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Extract GST data from this record: {text}"}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_json = json.loads(response.choices[0].message.content)
        canonical = CanonicalTransaction(**raw_json)
        
        return ExtractionResult(
            extraction_provider="openai",
            provider_model=self.model,
            canonical_data=canonical
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def transcribe_audio(self, audio_file_path: str):
        """Transcribes audio using Whisper API (kept for backward compatibility)"""
        with open(audio_file_path, "rb") as audio_file:
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        return transcript
