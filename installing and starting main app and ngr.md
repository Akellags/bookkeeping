### 1. How to install ngrok
Ngrok is a standalone `.exe`, not a Python package.
1.  **Download**: Go to [ngrok.com](https://ngrok.com/download) and download the Windows ZIP.
2.  **Extract**: Place `ngrok.exe` in your project folder (or anywhere in your PATH).
3.  **Auth**: Run `ngrok config add-authtoken YOUR_TOKEN` (get your token from the ngrok dashboard).

### 2. How to start your local machine
Open your terminal in the project root and run:
```bash
python -m uvicorn src.main:app --reload
```
*This starts the FastAPI server on `http://localhost:8000`.*

### 3. How to update Meta with the public URL
1.  **Start ngrok**: In a *separate* terminal, run:
    ```bash
    ngrok http 8000
    ```
2.  **Get URL**: Copy the `Forwarding` URL (it will look like `https://a1b2-c3d4.ngrok-free.app`).
3.  **Update Meta Dashboard**:
    - Go to [developers.facebook.com](https://developers.facebook.com/).
    - Select your App > **WhatsApp** > **Configuration**.
    - Click **Edit** next to **Webhook**.
    - **Callback URL**: Paste your ngrok URL + `/webhook` (e.g., `https://xyz.ngrok-free.app/webhook`).
    - **Verify Token**: Enter `help_u_verify_token` (matching your `.env`).
    - Click **Verify and Save**.
4.  **Subscribe**: In the same "Configuration" page, scroll down to **Webhook fields** and click **Manage**. Click **Subscribe** for `messages`.

**Note on Google Testing**: Since your `GOOGLE_REDIRECT_URI` is currently `localhost:8000`, the onboarding flow will work locally. Once you go live, you'll need to update that to your ngrok or production URL in both `.env` and the Google Cloud Console.

I've also updated the [./.env](./.env) with your Google credentials. You are now fully ready to test!