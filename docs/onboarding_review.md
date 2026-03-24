# Code Review: Onboarding Workflow

This review focuses on the security, reliability, and maintainability of the onboarding implementation in `src/main.py`, `src/db_service.py`, and `src/google_service.py`.

## 1. Security Vulnerabilities

### 🚨 WhatsApp ID Spoofing (High Risk)
- **Issue**: The `whatsapp_id` is passed as a plain-text `state` parameter in the Google OAuth URL (`/auth/google`).
- **Risk**: An attacker could initiate the OAuth flow and manually change the `state` parameter to someone else's phone number. If the attacker completes the OAuth flow with their own Google account, they could link their Google Drive to the victim's WhatsApp account, potentially hijacking data or injecting malicious transactions.
- **Recommendation**: Use a **Signed JWT** or a **Secure Session Cookie** for the `state` parameter to ensure it hasn't been tampered with.

### 🚨 Account Merging Logic (Medium Risk)
- **File**: `src/db_service.py` -> `save_user_token`
- **Issue**: If a user logs in with a Google account that already exists in the DB but with a different `whatsapp_id`, the system automatically "merges" them by returning the existing user's record.
- **Risk**: This could lead to unexpected behavior if a user changes phone numbers or if two users share a Google account.
- **Recommendation**: Explicitly handle "Change of WhatsApp Number" as a separate workflow with verification of the new number.

## 2. Reliability & Idempotency

### ⚠️ Drive Initialization Idempotency
- **File**: `src/google_service.py` -> `initialize_user_drive`
- **Issue**: The code creates a new "Help U" folder and "Master_Ledger" every time it's called for a new business. If the process fails halfway and is retried, it will create duplicate folders/files.
- **Recommendation**: Check for the existence of the "Help U" folder before creating it. Store the folder/file IDs and resume if partial setup is detected.

### ⚠️ Database Session Management
- **File**: `src/main.py` -> `google_callback`
- **Issue**: The code manually opens and closes `SessionLocal()`. If an exception occurs between `db = SessionLocal()` and `db.close()`, the connection might leak.
- **Recommendation**: Use a context manager (`with SessionLocal() as db:`) or the FastAPI `Depends(get_db)` pattern consistently.

## 3. Error Handling

### ⚠️ Brittle Error Redirects
- **File**: `src/main.py` -> `google_callback`
- **Issue**: Error messages are hardcoded strings parsed from exceptions (e.g., `if "active_business_id" in error_msg`).
- **Recommendation**: Use custom exception classes and catch specific API errors (e.g., `googleapiclient.errors.HttpError`) to provide more reliable error feedback.

## 4. Scalability

### ⚠️ Hardcoded Defaults
- **File**: `src/main.py`
- **Issue**: Business name "Help U Traders" and GSTIN "37ABCDE1234F1Z5" are hardcoded as defaults during onboarding.
- **Recommendation**: Move these to configuration or require the user to provide them immediately after OAuth before finalizing the setup.

---

## Summary of Recommendations
1. **Secure the State**: Sign the `state` parameter in OAuth.
2. **WhatsApp Verification**: Add a step to verify WhatsApp ownership (e.g., sending a unique code to the bot).
3. **Idempotent Drive Setup**: Ensure retrying onboarding doesn't clutter the user's Google Drive.
4. **Refactor DB Sessions**: Use context managers to prevent connection leaks.
