It is cleaner to keep your current OpenAI pipeline as-is and introduce **Google Document AI + Vertex AI** as a second extraction provider behind a feature flag, instead of mixing both in one pipeline. That fits your current architecture well because you already have a single FastAPI backend, WhatsApp ingestion, web uploads, Google Drive/Sheets integration, and an existing OpenAI-based image extraction flow. 

Below is a **developer-ready implementation spec** you can hand to the team.

---

# Implementation goal

Add a second invoice extraction offering:

* `openai_api = true` → use the **current OpenAI flow**
* `openai_api = false` → use the new **Google flow**

  * **Document AI** for invoice extraction from PDFs/images
  * **Vertex AI Gemini** only for normalization / optional repair inside the Google offering

This preserves your existing WhatsApp, FE, Google Drive, and Google Sheets flow while swapping only the extraction engine. Your current product already uses GPT Vision for image extraction and runs on GCP/Cloud Run, so this is a natural extension rather than a rewrite. 

Google’s current docs support the core parts this needs: Document AI supports PDFs and common image formats, recommends at least 200 DPI for OCR quality, and warns that lossy formats like JPEG can reduce accuracy; Vertex AI Gemini supports multimodal prompts and document understanding with PDFs. ([Google Cloud Documentation][1])

---

# 1. Product decision

## Offerings

Expose two extraction providers in the product:

* **OpenAI Extraction**

  * existing implementation
  * current default for existing users
* **Google Extraction**

  * Document AI + Vertex AI
  * available per tenant / subscription / admin setting

## Flag model

Do not use a single boolean long-term, even if you start with one.

### Immediate implementation

You can start with:

```python
openai_api: bool
```

### Recommended internal representation

Use:

```python
extraction_provider: Literal["openai", "google"]
```

Then keep backward compatibility:

```python
if openai_api is True:
    extraction_provider = "openai"
else:
    extraction_provider = "google"
```

This avoids pain later if you add a third provider.

---

# 2. Architecture change

## Current

```text
WhatsApp / FE Upload
    -> media preprocessing
    -> OpenAI extraction
    -> transaction normalization
    -> Google Sheets / Drive
```

## New

```text
WhatsApp / FE Upload
    -> media preprocessing
    -> Extraction Orchestrator
        -> Provider = OpenAI  -> existing OpenAI extractor
        -> Provider = Google  -> Document AI extractor + Gemini normalizer
    -> canonical transaction normalization
    -> validation
    -> Google Sheets / Drive
```

## Rule

Only the **extractor** changes by provider.

Everything else stays shared:

* upload handling
* auth
* Drive archival
* Sheets writeback
* transaction schema
* user-facing ledger
* WhatsApp responses
* dashboard rendering

That matches your current architecture, where AI extraction is one component inside a wider bookkeeping platform. 

---

# 3. Modules to add

Add these backend modules.

## New packages

```text
app/
  services/
    extraction/
      orchestrator.py
      base.py
      openai_extractor.py
      google_extractor.py
      normalizer.py
      validators.py
    google/
      document_ai_client.py
      vertex_ai_client.py
    media/
      file_type.py
      quality_checks.py
      pdf_utils.py
      image_utils.py
```

## New responsibilities

### `base.py`

Common extractor interface.

```python
from abc import ABC, abstractmethod
from app.schemas.extraction import ExtractionRequest, ExtractionResult

class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        ...
```

### `orchestrator.py`

Routes by provider flag.

### `openai_extractor.py`

Wrap existing logic with no functional change.

### `google_extractor.py`

Runs:

1. Document AI extraction
2. canonical field mapping
3. optional Vertex AI normalization/repair
4. confidence aggregation

### `document_ai_client.py`

Thin wrapper around Google Document AI.

### `vertex_ai_client.py`

Thin wrapper around Gemini for normalization only within Google flow.

---

# 4. Data model changes

Add provider-specific metadata without changing the canonical transaction shape.

## Existing canonical output should remain

```json
{
  "vendor_name": "",
  "invoice_number": "",
  "invoice_date": "",
  "subtotal": 0,
  "tax_amount": 0,
  "total_amount": 0,
  "currency": "INR",
  "gstin": "",
  "hsn_codes": [],
  "line_items": [],
  "payment_status": "",
  "source_channel": "whatsapp|web",
  "source_file_type": "pdf|jpg|png"
}
```

## Add extraction metadata

```json
{
  "extraction_provider": "openai|google",
  "provider_model": "gpt-4o-mini|documentai-invoiceparser+gemini",
  "provider_raw_response_path": "gs://...",
  "confidence_score": 0.91,
  "field_confidence": {
    "invoice_number": 0.96,
    "invoice_date": 0.88,
    "total_amount": 0.94
  },
  "needs_review": false,
  "review_reason": null
}
```

## DB migration

Add columns to the transaction / document-processing table:

```sql
ALTER TABLE document_jobs
ADD COLUMN extraction_provider VARCHAR(32) NOT NULL DEFAULT 'openai',
ADD COLUMN provider_model VARCHAR(128),
ADD COLUMN confidence_score FLOAT,
ADD COLUMN field_confidence JSONB,
ADD COLUMN provider_raw_response_path TEXT,
ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN review_reason TEXT;
```

If you store extraction per upload before ledger creation, put these there instead.

---

# 5. Config and secrets

## Environment variables

```bash
# Existing
OPENAI_API_KEY=...
OPENAI_API_ENABLED=true

# Google
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=us
DOCUMENT_AI_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=...
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-sa.json

# Feature defaults
DEFAULT_EXTRACTION_PROVIDER=openai
ENABLE_GOOGLE_EXTRACTION=true
ENABLE_OPENAI_EXTRACTION=true
```

## IAM / service account

Grant the Cloud Run service account:

* `roles/documentai.apiUser`
* `roles/aiplatform.user`
* storage access if raw responses are archived to GCS

Document AI requires processor setup and authenticated client access; Google’s client-library docs and quickstart cover the standard service-account pattern. ([Google Cloud Documentation][2])

---

# 6. Google Cloud setup

## Required services

Enable:

* Document AI API
* Vertex AI API
* Cloud Storage API, if archiving raw provider output there

## Document AI setup

Create an **Invoice Parser** processor in the chosen region.

Google’s processor list and Document AI overview document that invoice parsing is a supported processor type intended for structured data extraction from invoices. ([Google Cloud Documentation][3])

## Vertex AI setup

Use Gemini through Vertex AI for:

* value cleanup
* normalization to your schema
* missing-field repair from Document AI text/entities
* vendor-specific label mapping

Gemini on Vertex AI supports multimodal input and PDF-based document understanding, but in this offering it should be a post-extraction normalizer, not the primary parser. ([Google Cloud Documentation][4])

---

# 7. Request flow

## Shared ingestion flow

Applies to both WhatsApp and FE.

```text
1. Receive media
2. Detect mime type
3. Persist original file
4. Create document job
5. Load tenant config
6. Resolve extraction provider
7. Run extractor
8. Normalize to canonical schema
9. Validate totals / dates / GST fields
10. Persist result
11. Write to Sheets
12. Archive assets / provider output
13. Respond to user
```

## Provider resolution logic

```python
def resolve_provider(tenant_config) -> str:
    if tenant_config.extraction_provider:
        return tenant_config.extraction_provider
    if tenant_config.openai_api is True:
        return "openai"
    return "google"
```

---

# 8. API contract

## Tenant settings

Add to settings API:

```json
{
  "openai_api": true,
  "extraction_provider": "openai",
  "google_extraction_enabled": false
}
```

When switched:

* `openai_api=true` => `extraction_provider="openai"`
* `openai_api=false` => `extraction_provider="google"`

## Internal extraction request

```python
class ExtractionRequest(BaseModel):
    tenant_id: str
    user_id: str
    source_channel: Literal["whatsapp", "web"]
    file_path: str
    mime_type: str
    original_filename: str | None = None
    provider: Literal["openai", "google"]
    metadata: dict = {}
```

## Internal extraction result

```python
class ExtractionResult(BaseModel):
    provider: str
    provider_model: str
    raw_text: str | None = None
    canonical_data: dict
    confidence_score: float | None = None
    field_confidence: dict[str, float] = {}
    needs_review: bool = False
    review_reason: str | None = None
    raw_response_ref: str | None = None
```

---

# 9. Extractor implementation

## 9.1 Orchestrator

```python
class ExtractionOrchestrator:
    def __init__(self, openai_extractor, google_extractor):
        self.openai_extractor = openai_extractor
        self.google_extractor = google_extractor

    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        if req.provider == "openai":
            return await self.openai_extractor.extract(req)
        elif req.provider == "google":
            return await self.google_extractor.extract(req)
        raise ValueError(f"Unsupported provider: {req.provider}")
```

---

## 9.2 OpenAI extractor

This should be a wrapper around current behavior, unchanged.

```python
class OpenAIExtractor(BaseExtractor):
    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        # existing GPT-4o / GPT-4o-mini image/pdf logic
        # existing prompt
        # existing parsing into canonical schema

        return ExtractionResult(
            provider="openai",
            provider_model="gpt-4o-mini",  # or actual model used
            canonical_data=data,
            confidence_score=None,
            field_confidence={},
            needs_review=False,
        )
```

Do not refactor the prompt logic now unless needed.

---

## 9.3 Google extractor

### Flow

1. Determine file type
2. Call Document AI Invoice Parser
3. Convert entities/tables to internal raw structure
4. Map to canonical schema
5. Send Document AI output to Gemini for normalization
6. Compute review flags
7. Return canonical result

### Pseudocode

```python
class GoogleExtractor(BaseExtractor):
    def __init__(self, docai_client, vertex_client, normalizer, validator):
        self.docai_client = docai_client
        self.vertex_client = vertex_client
        self.normalizer = normalizer
        self.validator = validator

    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        docai_result = await self.docai_client.process_invoice(
            file_path=req.file_path,
            mime_type=req.mime_type,
        )

        mapped = self.normalizer.map_document_ai_to_canonical(docai_result)

        normalized = await self.vertex_client.normalize_invoice(
            raw_docai=docai_result,
            mapped_invoice=mapped,
            source_channel=req.source_channel,
        )

        final_data = self.normalizer.merge(mapped, normalized)

        validation = self.validator.validate(final_data)
        confidence = self.normalizer.compute_confidence(docai_result, final_data, validation)

        return ExtractionResult(
            provider="google",
            provider_model="documentai-invoiceparser+gemini",
            canonical_data=final_data,
            confidence_score=confidence.overall,
            field_confidence=confidence.by_field,
            needs_review=validation.needs_review,
            review_reason=validation.review_reason,
            raw_response_ref=docai_result.storage_ref,
        )
```

---

# 10. Document AI client

## Supported files

Accept:

* `application/pdf`
* `image/jpeg`
* `image/png`
* optionally TIFF if useful later

Document AI’s supported-file docs explicitly cover PDFs and common images and note that lossy formats can hurt quality. ([Google Cloud Documentation][1])

## Client example

```python
from google.cloud import documentai_v1 as documentai

class DocumentAIClient:
    def __init__(self, project_id: str, location: str, processor_id: str):
        self.client = documentai.DocumentProcessorServiceClient()
        self.name = self.client.processor_path(project_id, location, processor_id)

    async def process_invoice(self, file_path: str, mime_type: str):
        with open(file_path, "rb") as f:
            content = f.read()

        raw_document = documentai.RawDocument(
            content=content,
            mime_type=mime_type,
        )

        request = documentai.ProcessRequest(
            name=self.name,
            raw_document=raw_document,
        )

        result = self.client.process_document(request=request)
        return result.document
```

Google’s quickstart and client-library docs support this basic pattern. ([Google Cloud Documentation][2])

---

# 11. Vertex AI client

Use Gemini only after Document AI in this Google offering.

## Input to Gemini

Pass:

* raw OCR text
* extracted entities
* line items
* partially mapped canonical JSON

## Output

Force JSON-only output matching your internal schema.

## Prompt shape

```text
You are normalizing extracted invoice data for an Indian bookkeeping system.

You will receive:
1. OCR text from the invoice
2. entities extracted by Document AI
3. a partially mapped canonical invoice object

Tasks:
- normalize vendor_name
- normalize invoice_date to YYYY-MM-DD
- normalize totals as numeric strings
- map GSTIN
- map HSN/SAC values
- infer CGST/SGST/IGST split only if explicitly supported by the source data
- preserve uncertainty by returning null for missing fields
- do not invent line items

Return strict JSON matching this schema:
{
  "vendor_name": string|null,
  "invoice_number": string|null,
  "invoice_date": string|null,
  "subtotal": number|null,
  "tax_amount": number|null,
  "total_amount": number|null,
  "currency": string|null,
  "gstin": string|null,
  "hsn_codes": [string],
  "line_items": [
    {
      "description": string|null,
      "quantity": number|null,
      "unit_price": number|null,
      "amount": number|null,
      "hsn_code": string|null,
      "tax_rate": number|null
    }
  ]
}
```

## Model choice

Use a cost-efficient Gemini model on Vertex AI for structured normalization, not a heavyweight reasoning model unless needed. Current Vertex AI docs describe Gemini as multimodal and suitable for structured generation workflows. ([Google Cloud Documentation][4])

---

# 12. Canonical field mapping

Create one mapper from Document AI output to your internal invoice schema.

## Example field mapping table

| Canonical field  | Document AI source                    |
| ---------------- | ------------------------------------- |
| `vendor_name`    | supplier_name / vendor_name           |
| `invoice_number` | invoice_id / invoice_number           |
| `invoice_date`   | invoice_date                          |
| `subtotal`       | net_amount / subtotal                 |
| `tax_amount`     | total_tax_amount                      |
| `total_amount`   | total_amount                          |
| `currency`       | currency                              |
| `line_items[]`   | line_item entities                    |
| `gstin`          | OCR/entity parse from supplier tax id |
| `hsn_codes[]`    | line items or OCR regex extraction    |

Because your product explicitly needs GSTINs, HSN codes, amounts, and tax splits from bills/receipts, keep those fields canonical regardless of provider. 

## GST-specific logic

Since Document AI is generic invoice parsing, add your own Indian-tax normalization:

* regex GSTIN extraction
* HSN/SAC regex extraction
* IGST vs CGST+SGST inference
* tax split validation against totals

Do this in shared normalization logic so both providers align.

---

# 13. Validation and review logic

## Review triggers

Mark `needs_review=true` if any of these happen:

* missing `invoice_number`
* missing `total_amount`
* missing `invoice_date`
* line-item sum differs from total by tolerance
* tax math inconsistent beyond tolerance
* GSTIN malformed
* Document AI field confidence below threshold on key fields
* Gemini returns conflicting totals

## Suggested thresholds

```python
KEY_FIELD_MIN_CONFIDENCE = 0.75
AUTO_ACCEPT_CONFIDENCE = 0.90
AMOUNT_TOLERANCE = 1.0
DATE_PARSE_STRICT = True
```

## Output behavior

* High confidence: write to Sheets automatically
* Medium confidence: write with `review_pending`
* Low confidence: hold writeback or write to a review sheet

---

# 14. WhatsApp and FE behavior

## WhatsApp

No UX change required to enable Google extraction.

Flow:

1. receive media
2. download media
3. detect tenant provider
4. extract
5. send success/failure response

### Better WhatsApp messaging for Google provider

If image quality is poor:

* “Image is too blurry or cropped. Please resend clearly or upload PDF.”

This matters because Google notes image quality and JPEG compression can reduce Document AI accuracy. ([Google Cloud Documentation][1])

## Frontend

Add provider selector only in admin/settings, not per-upload unless you explicitly want that.

Suggested admin UI:

* Extraction Provider

  * OpenAI
  * Google

Optional display:

* Last extraction provider used
* Last confidence score
* Review status

---

# 15. Storage design

## Keep storing originals

Continue archiving originals to Google Drive as you already do. 

## Add provider raw output archive

Store raw provider output separately:

* `gs://helpu-raw-extraction/{tenant_id}/{doc_id}/documentai.json`
* `gs://helpu-raw-extraction/{tenant_id}/{doc_id}/gemini_normalized.json`

If you do not want GCS, store in PostgreSQL JSONB for smaller payloads, but GCS is better for audit/debug.

---

# 16. Error handling

## Provider-specific failures

### OpenAI path

No change.

### Google path

Handle separately:

* invalid mime type
* Document AI processor unavailable
* Document AI quota / auth errors
* Vertex AI timeout
* invalid JSON from Gemini normalizer

## Rule

Do not silently fall back from Google to OpenAI.

Since this is a distinct offering, fail inside the chosen provider and surface the correct error.

Example:

```python
if provider == "google":
    try:
        ...
    except DocumentAIError:
        return failure("google_extraction_failed", retryable=True)
```

That keeps product behavior honest and simplifies support.

---

# 17. Observability

Add structured logs:

```json
{
  "tenant_id": "...",
  "document_id": "...",
  "provider": "google",
  "source_channel": "whatsapp",
  "mime_type": "image/jpeg",
  "duration_ms": 1830,
  "confidence_score": 0.91,
  "needs_review": false
}
```

Metrics:

* extraction count by provider
* failure rate by provider
* average latency by provider
* review rate by provider
* key-field completeness by provider

This will let you compare OpenAI vs Google offering cleanly.

---

# 18. Rollout plan

## Phase 1

Backend only:

* provider config
* orchestrator
* Google extractor
* DB fields
* logs

## Phase 2

Internal QA:

* 100 sample docs across:

  * WhatsApp image
  * FE image
  * vendor PDF

## Phase 3

Private beta:

* enable Google provider for selected tenants only

## Phase 4

Admin UI toggle

* allow sales / ops to switch offering per tenant

---

# 19. Test plan

Create a fixed benchmark set:

* 30 vendor PDFs
* 30 frontend camera images
* 40 WhatsApp images

For each provider, measure:

* invoice number accuracy
* date accuracy
* total amount accuracy
* tax amount accuracy
* GSTIN extraction accuracy
* HSN extraction accuracy
* line-item completeness
* latency
* review rate

This is important because your current system is optimized around WhatsApp and image-driven bookkeeping, so WhatsApp image performance must be tested separately from PDFs. 

---

# 20. Developer task breakdown

## Backend

* add provider enum/config
* add extraction orchestrator
* wrap current OpenAI extractor
* implement Document AI client
* implement Vertex AI normalization client
* add shared validation layer
* add DB migration
* add raw output persistence
* add logs/metrics

## Frontend

* admin setting for provider
* display extraction metadata if needed

## DevOps

* enable APIs
* create Document AI processor
* provision service account + IAM
* mount credentials into Cloud Run or use workload identity

## QA

* prepare benchmark data
* compare providers
* verify Sheets writeback parity

---

# 21. Recommended code skeleton

```python
async def process_uploaded_document(job_id: str):
    job = repo.get_job(job_id)
    tenant = repo.get_tenant(job.tenant_id)

    provider = resolve_provider(tenant)

    req = ExtractionRequest(
        tenant_id=job.tenant_id,
        user_id=job.user_id,
        source_channel=job.source_channel,
        file_path=job.local_file_path,
        mime_type=job.mime_type,
        original_filename=job.original_filename,
        provider=provider,
        metadata=job.metadata or {},
    )

    result = await extraction_orchestrator.extract(req)

    repo.save_extraction_result(
        job_id=job.id,
        extraction_provider=result.provider,
        provider_model=result.provider_model,
        confidence_score=result.confidence_score,
        field_confidence=result.field_confidence,
        raw_response_ref=result.raw_response_ref,
        canonical_data=result.canonical_data,
        needs_review=result.needs_review,
        review_reason=result.review_reason,
    )

    if not result.needs_review:
        sheets_writer.write_transaction(result.canonical_data)
    else:
        review_queue.enqueue(job.id)

    notifier.send_processing_result(job, result)
```

---

# 22. My final recommendation

Ship it exactly as:

* **OpenAI offering** = current pipeline untouched
* **Google offering** = Document AI + Vertex AI
* shared downstream normalization, validation, Sheets/Drive writeback
* provider selected per tenant via flag

That is the cleanest product and engineering boundary.

The only design change I strongly recommend is this: internally, store `extraction_provider` as `"openai"` or `"google"` even if your external flag remains `openai_api=true/false`. That will save you a refactor later.

If you want, I can turn this into a **one-page engineering spec in markdown** with headings, acceptance criteria, env vars, and API payloads so you can paste it straight into Jira/Confluence.

[1]: https://docs.cloud.google.com/document-ai/docs/file-types?utm_source=chatgpt.com "Supported Files | Document AI"
[2]: https://docs.cloud.google.com/document-ai/docs/samples/documentai-quickstart?utm_source=chatgpt.com "Quickstart | Document AI"
[3]: https://docs.cloud.google.com/document-ai/docs/processors-list?utm_source=chatgpt.com "Processor list | Document AI"
[4]: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference?utm_source=chatgpt.com "Generate content with the Gemini API in Vertex AI"
