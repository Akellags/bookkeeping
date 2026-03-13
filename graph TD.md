graph TD
    subgraph "User Interface (WhatsApp)"
        A[User Mobile] -- Sends Bill Image / Voice / Text --> B(WhatsApp Cloud API)
    end

    subgraph "The 'Brain' (Backend Infrastructure)"
        B -- HTTPS Webhook --> C{FastAPI Backend}
        C -- Download Media ID --> B
        C -- Process JSON/Voice/Vision --> D[OpenAI GPT-4o-mini / Whisper]
        D -- Extracted GST Data --> C
        C -- Store User Metadata & Tokens --> E[(Supabase / SQLite)]
    end

    subgraph "The 'Database' (User's Google Drive)"
        C -- OAuth2 Refresh Token --> F[Google Drive API]
        F -- Upload Image --> G[Folder: /Help U/Purchases/]
        F -- Append Row --> H[Sheet: Master_Ledger]
        F -- Create & Export PDF --> I[Doc: Sales Invoice Template]
    end

    subgraph "SaaS Onboarding (Web Portal)"
        J[ReactJS Frontend] -- Authorize Google Drive --> K[Google OAuth2]
        K -- Refresh Token --> C
        J -- Stripe Checkout --> L[Payment Gateway]
        L -- Webhook --> C
    end

    subgraph "Monthly Compliance"
        M[Monthly Scheduler] -- Fetch Rows --> H
        M -- AI Validation & HSN Mapping --> D
        M -- Generate GSTR-1 CSV --> B
    end

    C -- Success Confirmation --> B
    B -- WhatsApp Message --> A

