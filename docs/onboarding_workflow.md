# Onboarding Workflow: Step-by-Step Process

This document outlines the complete onboarding workflow for the **Help U - Bookkeeper** application, detailing how a new user transitions from the web portal to the WhatsApp-based AI bookkeeper.

---

## 1. Web Portal Initiation (Frontend)
- **User Action**: The user visits the Help U web portal.
- **Entry Point**: A "Get Started" or "Onboard with WhatsApp" button.
- **Identification**: If the user is referred from WhatsApp, their `whatsapp_id` (phone number) is passed as a query parameter. If not, they are treated as a `new_user`.

## 2. Google Drive Authorization (OAuth2)
- **API Call**: `GET /auth/google?whatsapp_id={whatsapp_id}`
- **Process**:
    1. The backend generates a Google OAuth2 authorization URL with the `whatsapp_id` passed in the `state` parameter.
    2. The user is redirected to Google's consent screen.
    3. **Permissions Requested**:
        - `https://www.googleapis.com/auth/drive.file` (Create/Access Help U files)
        - `openid`, `https://www.googleapis.com/auth/userinfo.email` (User identity)
        - `https://www.googleapis.com/auth/documents` (Manage invoice templates)

## 3. Backend Authentication & Account Linking
- **Callback**: `GET /auth/callback?code={code}&state={whatsapp_id}`
- **Process**:
    1. **Token Exchange**: Backend exchanges the authorization code for an **Access Token** and a **Refresh Token**.
    2. **User Identification**: Backend fetches the user's email from Google.
    3. **Database Record**:
        - If `whatsapp_id` exists, it updates the record with the Google email and refresh token.
        - If `whatsapp_id` is "new_user", it generates a unique ID (e.g., `web_abcd123`).
        - If the email already exists under a different ID, it merges the records.
    4. **Persistence**: The **Refresh Token** is stored securely in the `users` table.

## 4. Google Drive Environment Initialization
- **Service**: `src.google_service.GoogleService.initialize_user_drive()`
- **Process** (Executed for new business profiles):
    1. **Folder Creation**: Creates a root folder named **"Help U"** in the user's Drive.
    2. **Master Ledger**: Creates a Google Sheet named **"Master_Ledger"** inside the "Help U" folder.
    3. **Header Setup**: Automatically populates the ledger with GSTR-1 compliant headers.
    4. **Invoice Template**:
        - Copies a master invoice template (if configured via `GOOGLE_INVOICE_TEMPLATE_ID`).
        - Fallback: Creates a basic Google Doc template with placeholders like `{{ business_name }}`, `{{ total_amount }}`, etc.

## 5. Business Profile Creation
- **Database Record**:
    1. A default business entry is created in the `businesses` table.
    2. **Default Settings**:
        - Name: "Help U Traders"
        - GSTIN: "37ABCDE1234F1Z5" (Mock/Sample)
    3. The `active_business_id` for the user is set to this new business.
    4. The Drive Folder ID, Sheet ID, and Template ID are linked to this business.

## 6. Onboarding Success & WhatsApp Handover
- **Redirect**: User is redirected to `/onboarding-success?whatsapp_id={whatsapp_id}`.
- **User Action**: The success page displays a "Start on WhatsApp" button.
- **URL**: `https://wa.me/{BOT_NUMBER}?text=Start`
- **Linkage**: The bot now recognizes the user's phone number as linked to their Google account and Drive.

## 7. Subscription & Payment (Post-Onboarding)
- **Status**: Users start with a `FREE_TRIAL`.
- **Upgrade Path**:
    1. User can upgrade via the web portal: `POST /api/billing/create-checkout-session`.
    2. Payments are handled via **Stripe**.
    3. **Webhook**: `POST /api/billing/webhook` updates the `subscription_status` to `PRO` upon successful payment.

---

## Current Implementation Status

| Step | Feature | Status | Implementation Details |
| :--- | :--- | :--- | :--- |
| 1 | OAuth2 Flow | ✅ Done | `src/main.py` (`/auth/google`, `/auth/callback`) |
| 2 | Account Merging | ✅ Done | `src/db_service.py` (`save_user_token`) |
| 3 | Drive Setup | ✅ Done | `src/google_service.py` (`initialize_user_drive`) |
| 4 | Ledger Headers | ✅ Done | GSTR-1 compliant headers automated |
| 5 | Invoice Template | ✅ Done | Automated doc creation with placeholders |
| 6 | Business Profiles | ✅ Done | Multi-business support via `businesses` table |
| 7 | Payment Gateway | ⚠️ Partial | Stripe integration implemented; needs production keys |
| 8 | WhatsApp Link | ⚠️ Partial | wa.me logic exists in docs, frontend needs verification |

## What's Missing / Next Steps
1. **WhatsApp Verification**: Currently, we trust the `whatsapp_id` passed in the state. For production, a verification step (OTP or signed token) might be needed.
2. **Template Customization**: Frontend UI to allow users to choose/upload their own invoice templates.
3. **GSTIN Validation**: Real-time validation of the GSTIN entered during onboarding.
4. **Onboarding Progress Tracker**: A UI component showing the user exactly which step they are on (Google linked -> Drive ready -> WhatsApp started).
