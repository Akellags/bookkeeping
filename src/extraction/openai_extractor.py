import os
import json
import logging
import httpx
import base64
import time
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
        Role: You are a specialist Indian GST Compliance Accountant and expert invoice data extraction system.
        Task: Analyze the provided image (bill) or text/voice transcript (sale) and extract data into a strict JSON format.

        Rules:
        1. Intent Detection: 
           - Set "is_transaction" to true if the message describes a sale, purchase, expense, payment (rent, bill, repair), or bill.
           - Set "is_transaction" to false if it's a greeting, casual chat, or irrelevant text.
           - Set "is_greeting" to true if the user is saying hi/hello.
           - Set "is_correction" to true if the user is correcting a previous entry (e.g., "Amount is 500").
           - Set "is_query" to true if the user is asking about their ledger data (e.g., "How much did I sell to Apollo?").
           - Set "is_consultant_query" to true if the user is asking for business advice, analysis, or performance checks (e.g., "Analyze my month", "Should I buy more from Apollo?").
        2. Identify GSTINs: Find both 'Supplier GSTIN' and 'Recipient GSTIN'.
        3. Items Extraction: ALWAYS extract items into the "items" list. Use ONLY the key "items" in the JSON.
        4. Descriptions: CRITICAL: Extract the EXACT description of the product/service as printed on the invoice. DO NOT summarize, DO NOT shorten, DO NOT capitalize if it is lowercase. Match the invoice text 1:1.
        5. Tax Split: Calculate or extract CGST, SGST, and IGST for each item. If the state of the supplier matches the recipient, use CGST/SGST. If different, use IGST.
        6. HSN Codes: Extract the 4 or 8-digit HSN code for each item. If missing, suggest the most likely 4-digit code based on the item description.
        7. Language: Convert any language invoice to English before extracting data.
        8. Standard Keys: Use snake_case for keys and avoid spaces or special characters.

        Required JSON Output Format:
        {
          "is_transaction": boolean,
          "is_greeting": boolean,
          "is_correction": boolean,
          "is_query": boolean,
          "is_consultant_query": boolean,
          "query_details": {
            "entity": "",
            "metric": "",
            "time_period": ""
          },
          "corrections": {},
          "transaction_type": "Purchase/Sale/Expense/Payment",
          "invoice_no": "",
          "date": "DD-MM-YYYY",
          "due_date": "DD-MM-YYYY",
          "vendor_name": "",
          "vendor_address": "",
          "vendor_gstin": "",
          "recipient_name": "",
          "recipient_address": "",
          "recipient_gstin": "",
          "place_of_supply": "",
          "reverse_charge": "Y/N",
          "items": [
            {
              "description": "",
              "hsn_code": "",
              "hsn_description": "",
              "uqc": "PCS/NOS/BOX/...",
              "quantity": 0.0,
              "rate": 0.0,
              "taxable_value": 0.0,
              "discount_amount": 0.0,
              "gst_rate": 0,
              "cgst": 0.0,
              "sgst": 0.0,
              "igst": 0.0,
              "total_amount": 0.0
            }
          ],
          "sub_total": 0.0,
          "tax_amount": 0.0,
          "discount_amount": 0.0,
          "shipping_cost": 0.0,
          "total_amount": 0.0,
          "notes": "",
          "terms_and_conditions": [],
          "payment_details": {
            "type": "Single/Recurring",
            "frequency": "Monthly/Yearly/N/A",
            "account_name": "",
            "account_number": "",
            "bank_name": "",
            "branch_name": "",
            "address": "",
            "swift_code": "",
            "ifs_code": "",
            "pan_number": ""
          }
        }
        """

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Processes a file and returns extracted transaction data in canonical format."""
        start_time = time.time()
        
        # Determine extraction type based on mime type
        if req.mime_type.startswith("image/"):
            result = await self._extract_from_image(req)
        elif req.mime_type == "application/pdf":
            # For OpenAI, we convert PDF to image for vision or use text if vision fails
            # Currently we convert in the caller, but let's assume we get image-like data if it's already converted
            result = await self._extract_from_image(req)
        else:
            # Fallback to text extraction for other types
            result = await self._extract_from_text(req)
            
        end_time = time.time()
        logger.info(f"TOTAL OpenAI Extraction took {end_time - start_time:.2f} seconds")
        return result

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
