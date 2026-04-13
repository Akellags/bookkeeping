from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field

class ExtractionRequest(BaseModel):
    user_id: str
    business_id: Optional[str] = None
    media_path: str
    mime_type: str
    extraction_provider: Literal["openai", "google", "local"] = "openai"
    context: Dict = {}
    prompt_override: Optional[str] = None

class LineItem(BaseModel):
    hsn_code: str = ""
    hsn_description: str = ""
    uqc: str = "OTH"
    quantity: float = 0.0
    gst_rate: int = 0
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_amount: float = 0.0

class CanonicalTransaction(BaseModel):
    is_transaction: bool = False
    is_greeting: bool = False
    is_correction: bool = False
    is_query: bool = False
    is_consultant_query: bool = False
    query_details: Dict = {}
    corrections: Dict = {}
    transaction_type: str = "Expense"
    payment_details: Dict = {"type": "Single", "frequency": "N/A"}
    invoice_no: str = ""
    date: str = ""
    vendor_name: str = ""
    vendor_gstin: str = ""
    recipient_name: str = ""
    recipient_gstin: str = ""
    place_of_supply: str = ""
    reverse_charge: str = "N"
    items: List[LineItem] = []
    total_amount: float = 0.0

class ExtractionResult(BaseModel):
    extraction_provider: str
    provider_model: str
    canonical_data: CanonicalTransaction
    confidence_score: Optional[float] = 0.0
    field_confidence: Dict[str, float] = {}
    raw_response_path: Optional[str] = None
    needs_review: bool = False
    review_reason: Optional[str] = None
