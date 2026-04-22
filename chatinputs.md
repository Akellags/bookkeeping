Found it.

Your inbound webhook is working. The reply is failing because your Meta access token includes a trailing newline:

```text
'Bearer ...QZDZD\r\n'
```

That `\r\n` at the end makes the `Authorization` header invalid.

## Focused fix

Strip whitespace when reading the token.

If you have something like:

```python
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
```

change it to:

```python
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
```

And when building headers:

```python
headers = {
    "Authorization": f"Bearer {META_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}
```

## Best place to patch

Anywhere you load the token for WhatsApp sends, do this:

```python
import os

def get_meta_token() -> str:
    token = os.getenv("META_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN is missing")
    return token
```

Then:

```python
token = get_meta_token()
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
```

## Also harden the verify token

Do the same for your verify token too:

```python
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
```

## Why this happened

Your secret value was likely stored or read with a newline at the end. Even though the secret itself may look fine, the app is clearly receiving it with `\r\n`, and Python’s HTTP client rejects it in headers.

## Optional debug line

Temporarily log the token length, not the token itself:

```python
token = os.getenv("META_ACCESS_TOKEN", "")
logger.info("META_ACCESS_TOKEN length before strip: %s", len(token))
logger.info("META_ACCESS_TOKEN length after strip: %s", len(token.strip()))
```

Do not log the token value.

## After patching

Redeploy Cloud Run, then test again by sending a WhatsApp message from your phone to the business number.

## If you want to clean the secret too

You can also re-add the secret cleanly:

```bash
echo -n "YOUR_META_ACCESS_TOKEN" | gcloud secrets versions add META_ACCESS_TOKEN --data-file=-
```

But even then, keep `.strip()` in code. It prevents this exact problem from coming back.

If you paste the function where you send the WhatsApp reply, I’ll rewrite that exact block.
