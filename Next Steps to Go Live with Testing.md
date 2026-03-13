### Next Steps to Go Live with Testing

Now that your **ngrok tunnel is active** (`https://postmuscular-nonefficiently-kenneth.ngrok-free.dev`), follow these steps precisely:

#### 1. Configure the Webhook in Meta Dashboard
1.  Go to [developers.facebook.com](https://developers.facebook.com/) > Your App > **WhatsApp** > **Configuration**.
2.  Click **Edit** next to "Webhook".
3.  **Callback URL**: `https://postmuscular-nonefficiently-kenneth.ngrok-free.dev/webhook`
4.  **Verify Token**: `help_u_secure_verify_2026` (Must match your `.env`).
5.  Click **Verify and Save**. (If this fails, ensure your FastAPI server is running with `uvicorn`).
6.  Scroll down to **Webhook fields** and click **Manage**.
7.  Find **`messages`** in the list and click **Subscribe**.

#### 2. Update Google OAuth (Important for Onboarding)
1.  Go to [Google Cloud Console](https://console.cloud.google.com/) > **APIs & Services** > **Credentials**.
2.  Edit your **OAuth 2.0 Client ID**.
3.  Add `https://postmuscular-nonefficiently-kenneth.ngrok-free.dev/auth/callback` to the **Authorized redirect URIs**.
4.  Update your [./.env](./.env) line 13:
    `GOOGLE_REDIRECT_URI=https://postmuscular-nonefficiently-kenneth.ngrok-free.dev/auth/callback`

#### 3. Send Your First Test Message
1.  On your mobile phone, open WhatsApp and send a message like:
    *"Bill for Apollo Pharm, 10 masks at 50 each, 18% GST"*
2.  **Watch your terminal**: You should see the incoming payload log in your FastAPI console.
3.  **The Response**: The bot should reply on WhatsApp with the extracted GST details.

#### 4. Test User Onboarding (The Portal)
1.  Open your browser and go to:
    `https://postmuscular-nonefficiently-kenneth.ngrok-free.dev/auth/google`
2.  Complete the Google login.
3.  The system should redirect you back and log that it received your **Refresh Token**. (This is the "Magic Link" part).

**Note**: Since we don't have a live database yet, I'm using a placeholder in the webhook. You'll see the AI result in your console first. Let me know when you've successfully received a response on WhatsApp!