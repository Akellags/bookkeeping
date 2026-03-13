-- User metadata and OAuth token storage
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id VARCHAR(50) UNIQUE NOT NULL, -- The user's phone number from Meta Cloud API
    google_email VARCHAR(100) UNIQUE NOT NULL, -- Email from Google OAuth
    google_refresh_token TEXT, -- OAuth2 Refresh Token for long-term Drive access
    drive_folder_id VARCHAR(100), -- Unique folder ID for "Help U" in user's Drive
    master_ledger_sheet_id VARCHAR(100), -- Unique sheet ID for Master_Ledger.gsheet
    subscription_status VARCHAR(20) DEFAULT 'FREE_TRIAL', -- FREE_TRIAL, ACTIVE, EXPIRED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Transaction logs (for audit and debugging)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    whatsapp_message_id VARCHAR(100) UNIQUE,
    transaction_type VARCHAR(20), -- Purchase, Sale, Report
    media_url TEXT, -- Link to the bill image (if purchase)
    extracted_json JSONB, -- The raw JSON output from OpenAI Vision
    status VARCHAR(20), -- PROCESSED, FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
