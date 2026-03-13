# Help U - WhatsApp-to-Drive Bookkeeper Implementation Plan

## 1. Project Overview
"Help U" is a serverless, AI-powered bookkeeping assistant for Indian traders. It leverages the WhatsApp Cloud API for the user interface, n8n/Python for backend logic, and OpenAI GPT-4o-mini for data extraction and processing. All financial data is stored directly in the user's Google Drive (Sheets/Docs) to ensure data sovereignty.

## 2. Core Modules
### Module A: Smart Purchase Capture
- **Input**: User sends a photo of a physical bill/receipt on WhatsApp.
- **Processing**:
    - Download media from WhatsApp Cloud API.
    - Analyze image using OpenAI GPT-4o-mini (Vision).
    - Extract: Vendor GSTIN, Date, HSN, Taxable Value, CGST/SGST/IGST.
- **Storage**:
    - Upload image to `UserDrive/Help U/Purchases/YYYY_MM/`.
    - Append data to `UserDrive/Help U/Master_Ledger.gsheet`.

### Module B: Conversational Sales Invoicing
- **Input**: Voice note or text description (e.g., "Bill for Apollo Pharm, 20 units Masks at 150 each, 12% GST").
- **Processing**:
    - Convert voice to text using OpenAI Whisper (if audio).
    - Parse details using GPT-4o-mini.
    - Calculate GST splits and totals.
- **Storage/Output**:
    - Fill a Google Doc template in the user's Drive.
    - Export as PDF.
    - Send PDF link back to user via WhatsApp.

### Module C: GST Portal Ready Reports
- **Trigger**: Monthly (e.g., 5th of each month) or manual trigger via bot.
- **Processing**:
    - Read the `Master_Ledger` sheet from the user's Drive.
    - Validate GSTINs and HSN codes (fill gaps using AI).
    - Format data for GSTR-1 Offline Tool (CSV/JSON).
- **Delivery**: Send the formatted file to the user via WhatsApp.

## 3. Technical Stack & Deployment
- **Interface**: WhatsApp Cloud API (Meta).
- **Backend Logic**: 
    - **Option A (Python)**: AWS Lambda or Google Cloud Functions (Serverless). Highly scalable, pay-per-use.
    - **Option B (n8n)**: Self-hosted on a DigitalOcean Droplet ($6/mo). Maximum control over workflows.
- **Frontend**: ReactJS (Admin/Onboarding Portal).
- **AI Intelligence**: OpenAI API (GPT-4o-mini for Vision & NLP, Whisper for Audio).
- **Database/Storage**: Google Drive API (Primary Storage), Supabase/PostgreSQL (Metadata & User Accounts).
- **Authentication**: OAuth2 (`https://www.googleapis.com/auth/drive.file`).

## 4. Implementation Roadmap (4 Days)
- **Day 1: Infrastructure & Auth**
    - Setup Meta Developer Account and WhatsApp Cloud API.
    - Setup Google Cloud Console Project and OAuth2.
    - Create Google Doc and Sheet templates.
- **Day 2: Purchase Scan Workflow**
    - Implement WhatsApp Webhook.
    - Build media download and OpenAI Vision integration.
    - Implement Google Sheets append logic.
- **Day 3: Sales Prompt Workflow**
    - Build Voice-to-Text and NLP parsing logic.
    - Implement Google Doc template filling and PDF export.
    - Implement WhatsApp media message response.
- **Day 4: GST Export & Testing**
    - Build report generation script (GSTR-1 format).
    - Implement monthly trigger/reminder logic.
    - Pilot testing with paper bills and various invoice formats.

## 5. Security & Privacy
- **User Ownership**: No user data is stored on "Help U" servers. All ledger entries and documents live in the user's personal Google Drive.
- **Fetch & Forget**: The system only accesses user sheets temporarily during report generation using the OAuth Refresh Token.
- **Strict Scopes**: Only `drive.file` scope is used to limit access to files created by the app.
