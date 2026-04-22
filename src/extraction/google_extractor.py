import logging
import json
import time
from src.extraction.base import BaseExtractor
from src.extraction.schemas import ExtractionRequest, ExtractionResult, CanonicalTransaction
from src.google.document_ai_client import GoogleDocumentAIClient
from src.google.vertex_ai_client import GoogleVertexAIClient

logger = logging.getLogger(__name__)

class GoogleExtractor(BaseExtractor):
    def __init__(self):
        self.doc_ai = GoogleDocumentAIClient()
        self.vertex_ai = GoogleVertexAIClient()
        self.normalization_prompt = """
        Role: You are a specialist Indian GST Compliance Accountant and expert invoice data extraction system.
        Task: Analyze the raw extraction data from an invoice and normalize it into a strict JSON format.

        Rule: Extract all line items correctly. Handle discounts and schemes carefully.
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
        7. Discounts: If an item has a "Discount" or "Scheme Discount" amount, extract it into "discount_amount". The "taxable_value" should be (quantity * rate) - discount_amount.
        8. Language: Convert any language invoice to English before extracting data.
        9. Standard Keys: Use snake_case for keys and avoid spaces or special characters.

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

    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Prioritizes direct Gemini extraction for speed, fallbacks to Document AI."""
        from src.utils import compress_image
        start_time = time.time()
        
        # Optimize image for faster upload and processing
        media_path = req.media_path
        is_compressed = False
        if req.mime_type.startswith("image/"):
            media_path = compress_image(req.media_path)
            if media_path != req.media_path:
                is_compressed = True
        
        try:
            # 1. Primary Path: Direct Gemini Extraction (Vision/Multimodal)
            try:
                logger.info(f"Primary Path: Direct Gemini Extraction for user: {req.user_id}")
                gemini_start = time.time()
                normalized_data = await self.vertex_ai.extract_from_media(
                    media_path,
                    req.mime_type,
                    self.normalization_prompt
                )
                gemini_end = time.time()
                logger.info(f"Direct Gemini extraction took {gemini_end - gemini_start:.2f} seconds")
                
                # Cleanup compressed image
                if is_compressed and os.path.exists(media_path):
                    os.remove(media_path)
                
                canonical = CanonicalTransaction(**normalized_data)
                end_time = time.time()
                logger.info(f"TOTAL Direct Google Extraction took {end_time - start_time:.2f} seconds")

                return ExtractionResult(
                    extraction_provider="google",
                    provider_model=f"{self.vertex_ai.model_name} (Direct)",
                    canonical_data=canonical,
                    confidence_score=0.95 # Native Gemini confidence placeholder
                )
            except Exception as gemini_err:
                logger.warning(f"Direct Gemini extraction failed, falling back to Document AI: {gemini_err}")
            
            # 2. Fallback Path: Document AI + Vertex AI Normalization
            doc_start = time.time()
            document = await self.doc_ai.process_document(req.media_path, req.mime_type)
            doc_end = time.time()
            logger.info(f"Document AI fallback extraction took {doc_end - doc_start:.2f} seconds")
            
            raw_data = self._doc_to_dict(document)
            
            vertex_start = time.time()
            normalized_data = await self.vertex_ai.normalize_extraction(
                raw_data, 
                self.normalization_prompt
            )
            vertex_end = time.time()
            logger.info(f"Vertex AI fallback normalization took {vertex_end - vertex_start:.2f} seconds")
            
            canonical = CanonicalTransaction(**normalized_data)
            
            total_confidence = sum(entity.confidence for entity in document.entities)
            avg_confidence = total_confidence / len(document.entities) if document.entities else 0.0
            
            field_confidence = {
                entity.type_: entity.confidence for entity in document.entities
            }

            end_time = time.time()
            logger.info(f"TOTAL Fallback Google Extraction took {end_time - start_time:.2f} seconds")

            return ExtractionResult(
                extraction_provider="google",
                provider_model="documentai-fallback + gemini-normalization",
                canonical_data=canonical,
                confidence_score=avg_confidence,
                field_confidence=field_confidence
            )

        except Exception as e:
            logger.error(f"Google Extraction failed entirely: {e}")
            raise

    async def extract_text(self, text: str) -> dict:
        """Processes a text message or transcript using Gemini (Async)."""
        logger.info("Processing text with Gemini")
        start_time = time.time()
        try:
            # We reuse the normalization prompt which is already strict JSON
            result = await self.vertex_ai.normalize_extraction(
                {"user_input": text}, 
                self.normalization_prompt
            )
            end_time = time.time()
            logger.info(f"Gemini text processing took {end_time - start_time:.2f} seconds")
            return result
        except Exception as e:
            logger.error(f"Gemini text processing failed: {e}")
            return None

    def _doc_to_dict(self, document) -> dict:
        """Converts Document AI entities into a simple dictionary."""
        entities = []
        for entity in document.entities:
            entity_data = {
                "type": getattr(entity, "type_", ""),
                "mention_text": getattr(entity, "mention_text", ""),
                "confidence": float(getattr(entity, "confidence", 0.0)),
            }
            
            # Safely get normalized value
            normalized = getattr(entity, "normalized_value", None)
            if normalized:
                # Try common fields for normalized values
                norm_text = getattr(normalized, "text", None)
                if not norm_text:
                    # Fallback to string representation if text is missing
                    norm_text = str(normalized).strip()
                entity_data["normalized_value"] = norm_text
            else:
                entity_data["normalized_value"] = None
                
            entities.append(entity_data)
            
        return {
            "text": getattr(document, "text", ""),
            "entities": entities
        }
