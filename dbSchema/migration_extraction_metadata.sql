-- Migration: Add Extraction Metadata to Transactions
ALTER TABLE transactions
ADD COLUMN extraction_provider VARCHAR(32) NOT NULL DEFAULT 'openai',
ADD COLUMN provider_model VARCHAR(128),
ADD COLUMN confidence_score JSONB,
ADD COLUMN field_confidence JSONB,
ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN review_reason TEXT;
