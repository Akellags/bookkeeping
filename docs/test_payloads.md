# Postman Testing Guide for Help U

To test the backend without using live WhatsApp, send a `POST` request to `http://localhost:8000/webhook`.

## 1. Test Purchase Scan (Image Upload)
**Method**: `POST`
**Body (JSON)**:
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "8234567890",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "1234567890",
              "phone_number_id": "919339574596127"
            },
            "contacts": [{ "wa_id": "919999999999", "profile": { "name": "Test User" } }],
            "messages": [
              {
                "from": "919999999999",
                "id": "wamid.HBgLOTExMTExMTE",
                "timestamp": "1692222222",
                "type": "image",
                "image": {
                  "id": "123456789012345",
                  "mime_type": "image/jpeg",
                  "sha256": "sample_sha"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

## 2. Test Sales Prompt (Text)
**Method**: `POST`
**Body (JSON)**:
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "8234567890",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "messages": [
              {
                "from": "919999999999",
                "type": "text",
                "text": { "body": "Bill for Apollo Pharm, 20 units Masks at 150 each, 12% GST." }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```
