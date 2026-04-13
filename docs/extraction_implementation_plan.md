# Implementation Plan: Google Document AI & Vertex AI Integration

## Overview
Introduce a modular extraction system that supports both OpenAI (current) and Google Cloud (new) providers, with a focus on maintainability and future extensibility (e.g., local LLMs).

## Architecture
The new architecture will use an Orchestrator pattern to route extraction requests to the appropriate provider based on tenant settings or feature flags.

### Directory Structure
```text
src/
  extraction/
    __init__.py
    base.py            # Abstract Base Class for extractors
    schemas.py         # Pydantic models for request/result
    orchestrator.py    # Routing logic
    openai_extractor.py # Current OpenAI logic
    google_extractor.py # New Google logic
    normalizer.py       # (Optional) Canonical data cleaning
  google/
    __init__.py
    document_ai_client.py
    vertex_ai_client.py
```

## Phase 1: Foundation & Abstraction
1.  **Define Schemas**: Create `ExtractionRequest` and `ExtractionResult` in `src/extraction/schemas.py`.
2.  **Define Base Class**: Create `BaseExtractor` in `src/extraction/base.py`.
3.  **Port OpenAI**: Move existing logic from `AIProcessor` to `OpenAIExtractor`.

## Phase 2: Google Integration
1.  **Clients**: Implement thin wrappers for Document AI and Vertex AI in `src/google/`.
2.  **Google Extractor**: 
    - Call Document AI for structured OCR.
    - Map Document AI entities to canonical transaction schema.
    - Use Vertex AI (Gemini) for normalization and "repairing" missing fields if needed.

## Phase 3: Orchestration & Configuration
1.  **Orchestrator**: Implement `ExtractionOrchestrator` to handle provider selection.
2.  **Config**: Add environment variables for Google Project, Location, Processor ID, etc.
3.  **Feature Flags**: Implement logic to resolve provider based on user settings or defaults.

## Phase 4: Data Model & Persistence
1.  **Database Migration**: Add extraction metadata columns to the `transactions` table.
    - `extraction_provider`
    - `provider_model`
    - `confidence_score`
    - `field_confidence` (JSON)
    - `needs_review`
    - `review_reason`
2.  **Update `Transaction` Model**: Reflect these changes in `src/db_service.py`.

## Phase 5: Integration & Refactoring
1.  **Frontend API**: Update `src/api/frontend.py` to use the new Orchestrator.
2.  **WhatsApp Bot**: Update `src/bot/handlers/interactive.py` to use the new Orchestrator.
3.  **Cleanup**: Refactor `AIProcessor` or deprecate it in favor of the new system.

## Local LLM Readiness
By using a `BaseExtractor` and `ExtractionRequest/Result` schemas, adding a local LLM provider (e.g., using Ollama or vLLM) will only require implementing a new `LocalExtractor` class.

## Best Practices
- **Idempotency**: Maintain existing deduplication logic.
- **Logging**: Detailed logging for extraction steps and confidence scores.
- **Error Handling**: Graceful fallback or clear error messages for extraction failures.
- **Security**: Use GCP Service Account for authentication.
