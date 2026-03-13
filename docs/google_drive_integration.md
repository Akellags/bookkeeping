# Google Drive Integration & Data Privacy

This document explains how the Help U Bookkeeper interacts with a user's Google Drive and ensures data privacy through the "User-Owned Data" model.

## 1. Architecture: The "User-Owned Data" Model
Unlike traditional SaaS apps that store all user data in a central database, Help U stores all financial records (images, spreadsheets, PDFs) directly in the **User's Personal Google Drive**. 

- **Storage Location**: `User's Google Drive` > `Help U` folder.
- **Ownership**: The user owns 100% of their data. If they stop using the service, their records remain in their Drive.
- **Access Control**: The app uses the **OAuth2 `drive.file` scope**, which strictly limits the app's access to only files and folders it has created. It cannot see or read any other personal files in the user's Drive.

## 2. Authentication & Authorization Flow

1.  **Frontend Trigger**: User clicks the "Connect Google" button on the onboarding page.
2.  **OAuth2 Request**: The app requests the following scopes:
    - `https://www.googleapis.com/auth/drive.file`: To create and manage its own files.
    - `https://www.googleapis.com/auth/userinfo.email`: To identify the user and link their account.
    - `openid`: For secure authentication.
3.  **Token Exchange**: 
    - Google provides an `Authorization Code`.
    - The backend exchanges this code for an `Access Token` (temporary) and a **`Refresh Token`** (long-lived).
4.  **Secure Storage**: The `Refresh Token` is encrypted and stored in the application's metadata database, linked to the user's WhatsApp phone number.

## 3. The "Bridge" Process (WhatsApp to Drive)

When a user interacts with the WhatsApp bot, the system acts as a temporary bridge:

1.  **Incoming Message**: User sends a bill image or a voice note via WhatsApp.
2.  **AI Extraction**: The "Brain" (OpenAI) extracts the GST data into a JSON format.
3.  **Token Retrieval**: The system fetches the user's stored `Refresh Token` from the database.
4.  **Google Service Execution**:
    - **Initialization**: If it's the first time, it creates the `Help U` folder and `Master_Ledger` spreadsheet.
    - **Upload**: The bill image is uploaded to the user's `Help U/Purchases` folder.
    - **Logging**: The extracted data is appended as a new row in the user's `Master_Ledger` sheet.
5.  **Clean Up**: The system "forgets" the data after the operation is complete, maintaining the "Fetch & Forget" privacy principle.

## 4. Security Benefits
- **Zero-Data Hosting**: The service provider does not host sensitive financial data, reducing liability and data breach risks.
- **Transparency**: Users can open their Google Drive at any time to see the images and spreadsheets being generated in real-time.
- **Revocable Access**: Users can revoke the app's access at any time through their Google Account Security settings.
