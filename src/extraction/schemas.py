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
    description: str = ""
    hsn_code: Optional[str] = ""
    hsn_description: Optional[str] = ""
    uqc: Optional[str] = "OTH"
    quantity: Optional[float] = 0.0
    rate: Optional[float] = 0.0
    taxable_value: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    gst_rate: Optional[int] = 0
    cgst: Optional[float] = 0.0
    sgst: Optional[float] = 0.0
    igst: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0

class CanonicalTransaction(BaseModel):
    is_transaction: bool = False
    is_greeting: bool = False
    is_correction: bool = False
    is_query: bool = False
    is_consultant_query: bool = False
    query_details: Optional[Dict] = {}
    corrections: Optional[Dict] = {}
    transaction_type: str = "Expense"
    invoice_no: Optional[str] = ""
    date: Optional[str] = ""
    due_date: Optional[str] = ""
    vendor_name: Optional[str] = ""
    vendor_address: Optional[str] = ""
    vendor_gstin: Optional[str] = ""
    recipient_name: Optional[str] = ""
    recipient_address: Optional[str] = ""
    recipient_gstin: Optional[str] = ""
    place_of_supply: Optional[str] = ""
    reverse_charge: Optional[str] = "N"
    items: List[LineItem] = []
    sub_total: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    shipping_cost: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    notes: Optional[str] = ""
    terms_and_conditions: List[str] = []
    payment_details: Optional[Dict] = {
        "type": "Single",
        "frequency": "N/A",
        "account_name": "",
        "account_number": "",
        "bank_name": "",
        "branch_name": "",
        "address": "",
        "swift_code": "",
        "ifs_code": "",
        "pan_number": ""
    }

class ExtractionResult(BaseModel):
    extraction_provider: str
    provider_model: str
    canonical_data: CanonicalTransaction
    confidence_score: Optional[float] = 0.0
    field_confidence: Dict[str, float] = {}
    raw_response_path: Optional[str] = None
    needs_review: bool = False
    review_reason: Optional[str] = None
