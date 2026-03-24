# Help U - WhatsApp Greeting & Welcome Flow

This document details the technical flow when a user sends a greeting (e.g., "Hi") to the Help U WhatsApp number.

---

## 🚀 The Welcome Message Flow

### 1. Entry Point
*   **Webhook Route**: `@app.post("/webhook")` in [./src/main.py](./src/main.py).
*   **Trigger**: User sends a text message containing "Hi", "Hello", "Help", or "Menu".

### 2. Logic Implementation
When a message is received, the following steps occur within the `handle_whatsapp_message` function:

1.  **Text Extraction**: The system extracts the message body and converts it to lowercase.
2.  **Keyword Detection**:
    ```python
    if text.lower() in ["help", "menu", "hi", "hello"]:
    ```
3.  **State Cleanup**:
    *   Before sending the welcome message, the system checks if the user has any "stale" interaction states (like being in the middle of an advice request or an edit).
    *   It clears `last_interaction_type` and `last_interaction_data` in the database to ensure a clean start.
4.  **Message Construction**:
    *   A multi-line string is prepared containing the branding and the list of available features with their respective emojis and command examples.

### 3. The Response (Welcome Message)
The user receives the following interactive help menu:

> Welcome to Help U! 🚀
>
> Commands:
> 📸 *Send a photo* of any bill to record it.
> 🎤 *Send a voice note* or text to record a sale (e.g., 'Sold items for 500').
> 📄 *'Send invoice INV-123'* to get a PDF link.
> 📊 *'Stats'* to see your monthly totals.
> 📈 *'Analysis'* for a deep business report.
> 💡 *'Advice'* to ask me anything about your business.
> 🧾 *'GSTR1'* to download your monthly JSON report.

### 4. Technical Execution
*   **Function**: `send_whatsapp_text(user_whatsapp_id, help_msg)`
*   **Utility**: Defined in [./src/utils.py](./src/utils.py), this function sends the POST request to the Meta WhatsApp Business API endpoint.
*   **Idempotency**: The `message_id` from the incoming request is stored in the `processed_messages` table to prevent duplicate responses if the webhook is retried by Meta.

---

## 🛠 Related Files
*   **Routing Logic**: [./src/main.py](./src/main.py:993:1015)
*   **API Utilities**: [./src/utils.py](./src/utils.py)
*   **Database Service**: [./src/db_service.py](./src/db_service.py)
