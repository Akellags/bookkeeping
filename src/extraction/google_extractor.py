import logging
import json
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
        Role: You are a specialist Indian GST Compliance Accountant.
        Task: Analyze the raw extraction data from an invoice and normalize it into a strict JSON format.

        Rules:
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

    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Runs Document AI extraction then Vertex AI normalization."""
        try:
            # 1. Document AI Extraction (Async call to client)
            document = await self.doc_ai.process_document(req.media_path, req.mime_type)
            
            # Convert Document AI entities to a dict for normalization
            raw_data = self._doc_to_dict(document)
            
            # 2. Vertex AI Normalization
            normalized_data = await self.vertex_ai.normalize_extraction(
                raw_data, 
                self.normalization_prompt
            )
            
            canonical = CanonicalTransaction(**normalized_data)
            
            # Confidence score (average of Document AI entity confidences)
            total_confidence = sum(entity.confidence for entity in document.entities)
            avg_confidence = total_confidence / len(document.entities) if document.entities else 0.0
            
            field_confidence = {
                entity.type_: entity.confidence for entity in document.entities
            }

            return ExtractionResult(
                extraction_provider="google",
                provider_model="documentai-invoice-parser + gemini-1.5-flash",
                canonical_data=canonical,
                confidence_score=avg_confidence,
                field_confidence=field_confidence
            )

        except Exception as e:
            logger.error(f"Google Extraction failed: {e}")
            raise

    def _doc_to_dict(self, document) -> dict:
        """Converts Document AI entities into a simple dictionary."""
        data = {"text": document.text, "entities": []}
        for entity in document.entities:
            data["entities"].append({
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": entity.confidence,
                "normalized_value": getattr(entity, 'normalized_value', {}).get('text')
            })
        return data
