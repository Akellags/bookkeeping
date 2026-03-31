# Help U - WhatsApp Features Deep Dive Implementation Document

This document provides a deep understanding of each WhatsApp command/option provided in the welcome message. It covers the flow from entry point to final response for each feature.

---

## 📸 Option 1: Record Bill (Image)
**"Send a photo of any bill to record it."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "image"`.

### 2. Implementation Flow
1.  **Media Retrieval**: 
    *   The `image_id` is extracted from the message payload.
    *   `get_whatsapp_media_url` and `download_whatsapp_media` from [./src/utils.py](./src/utils.py) are called to fetch the media URL and download the file locally as `temp_{image_id}.jpg`.
2.  **Pending Record Creation**:
    *   A new record is added to the `transactions` table in the database with status `PENDING_TYPE` and the local media path stored in `media_url`.
3.  **User Interaction (Stage 1)**:
    *   `send_whatsapp_interactive` is called to send two buttons: **"Sale Receipt"** and **"Purchase Invoice"**.
4.  **Button Response Handling**:
    *   When the user clicks a button, the webhook receives an `interactive` message.
    *   The pending transaction is fetched from the database based on the `user_whatsapp_id`.
    *   If **"Purchase Invoice"** or **"Sale Receipt"** is chosen, `AIProcessor.process_purchase_image` in [./src/ai_processor.py](./src/ai_processor.py) is called with the base64-encoded image.
5.  **AI Extraction**:
    *   The `gpt-5.4-mini` model with vision capabilities parses the bill for GSTINs, HSN codes, dates, amounts, and tax splits based on the `system_prompt`.
6.  **Ledger Update**:
    *   `GoogleService.append_to_master_ledger` in [./src/google_service.py](./src/google_service.py) appends the extracted JSON data to the user's "Master_Ledger" Google Sheet.
    *   The image is uploaded to the "Help U" folder on the user's Google Drive via `GoogleService.upload_bill_image`.
7.  **Final Interaction (Stage 2)**:
    *   If it's a "Sale", a PDF invoice is generated via `GoogleService.generate_sales_invoice`.
    *   The user is asked for payment status: **"Paid"** or **"Credit"** via buttons.
    *   If **"Credit"** is chosen, the system waits for a "Due Date" text input.

---

## 🎤 Option 2: Record Sale (Voice/Text)
**"Send a voice note or text to record a sale (e.g., 'Sold items for 500')."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "audio"` or `message_type == "text"`.

### 2. Implementation Flow
1.  **Audio Processing (If Voice Note)**:
    *   `audio_id` is extracted, downloaded, and passed to `TranscriptionService.transcribe_audio` in [./src/transcription_service.py](./src/transcription_service.py).
    *   The `faster-whisper` model (local inference) transcribes the audio into text.
2.  **AI Intent & Extraction**:
    *   The text (original or transcribed) is passed to `AIProcessor.process_sales_text` in [./src/ai_processor.py](./src/ai_processor.py).
    *   The AI detects if `is_transaction` is true and extracts data like `total_amount`, `vendor_name`, etc.
3.  **Confirmation Request**:
    *   A pending transaction is stored in the DB with status `PENDING_CONFIRM`.
    *   The system sends interactive buttons: **"Confirm"** and **"Cancel"**.
4.  **Finalization**:
    *   On **"Confirm"**, the data is appended to the Google Sheet via `GoogleService.append_to_master_ledger`.
    *   The user is then prompted for payment status (**"Paid"** / **"Credit"**) as in the image flow.

---

## 📄 Option 3: Send Invoice
**"'Send invoice INV-123' to get a PDF link."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "text"` and string starts with **"send invoice"**.

### 2. Implementation Flow
1.  **Parsing**: The invoice number (e.g., `INV-123`) is extracted from the message string.
2.  **URL Construction**: A dynamic link is generated pointing to the internal API: `/api/user/invoice/pdf?whatsapp_id={user_whatsapp_id}&invoice_no={invoice_no}`.
3.  **PDF Generation (On Demand)**:
    *   When the user clicks the link, the backend route `/api/user/invoice/pdf` (in [./src/main.py](./src/main.py)) is hit.
    *   It calls `GoogleService.generate_invoice_pdf_buffer` in [./src/google_service.py](./src/google_service.py).
    *   The service fetches the specific row from the Google Sheet and uses `reportlab` to draw a professional GST invoice.
4.  **Response**: The user receives the link in WhatsApp, which opens the generated PDF in their browser.

---

## 📊 Option 4: Stats
**"'Stats' to see your monthly totals."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "text"` and equals **"stats"**.

### 2. Implementation Flow
1.  **Data Fetching**:
    *   `GoogleService.get_ledger_stats` in [./src/google_service.py](./src/google_service.py) is called.
    *   It reads all rows from the Google Sheet, filters by the current month, and aggregates `total_sales`, `total_purchases`, and the count of transactions.
2.  **Response**:
    *   A formatted message is sent back:
        *   💰 *Total Sales:* ₹X,XXX
        *   🛒 *Total Purchases:* ₹X,XXX
        *   🧾 *Total Invoices:* X

---

## 📈 Option 5: Analysis
**"'Analysis' for a deep business report."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "text"` and equals **"analysis"**.

### 2. Implementation Flow
1.  **Business Summary**:
    *   `GoogleService.get_business_summary` in [./src/google_service.py](./src/google_service.py) aggregates the entire ledger into a structured summary (Monthly totals, Top Customers, Overdue payments, GST collections).
2.  **Expert Analysis**:
    *   The summary is passed to `ConsultantAgent.analyze_business` in [./src/consultant_agent.py](./src/consultant_agent.py).
    *   The `gpt-5.4-mini` model (Help U Expert role) analyzes the growth, risks, and GST compliance.
3.  **Response**: A conversational report is sent with emojis and professional advice (max 3-4 paragraphs).

---

## 💡 Option 6: Advice
**"'Advice' to ask me anything about your business."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "text"` and equals **"advice"**.

### 2. Implementation Flow
1.  **State Initialization**:
    *   The system sends a prompt asking the user to state their question.
    *   The user's record in the DB is updated with `last_interaction_type = "AWAITING_ADVICE"`.
2.  **User Question Processing**:
    *   The next message from the user is caught by the state machine in `main.py`.
    *   `GoogleService.get_business_summary` provides the context.
    *   `ConsultantAgent.analyze_business` is called with both the **Business Summary** and the **User's specific question**.
3.  **State Clearing**:
    *   The `last_interaction_type` is reset to `None` in the DB.
---

## 🧾 Option 7: GSTR1 Report
**"'GSTR1' to download your monthly JSON report."**

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Detection**: `message_type == "text"` and equals **"gstr1"**.

### 2. Implementation Flow
1.  **JSON Generation**:
    *   `GoogleService.generate_gstr1_json` in [./src/google_service.py](./src/google_service.py) is called.
    *   It processes all sales transactions for the current month and formats them into a government-compliant GSTR-1 JSON structure.
2.  **File Orchestration**:
    *   The JSON data is saved to a temporary local file: `GSTR1_{GSTIN}_{FP}.json`.
3.  **Media Delivery**:
    *   `upload_whatsapp_media` uploads the JSON file to Meta's servers and retrieves a `media_id`.
    *   `send_whatsapp_document` is called to deliver the file directly to the user's WhatsApp chat.
4.  **Cleanup**: The temporary local file is deleted immediately after sending.
