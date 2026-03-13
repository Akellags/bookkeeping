# Help U - Feature Roadmap

This document outlines the strategic next steps to move the Help U Bookkeeper from MVP to a full-featured SaaS product.

## 1. "Magic" PDF Invoice Generation (Module B)
- **Goal**: Automatically generate and deliver professional invoices.
- **Workflow**:
    - User records a sale via WhatsApp.
    - System fills a Google Doc template in the user's Drive.
    - System converts the Doc to PDF.
    - System sends the PDF link or file back to the user on WhatsApp.
- **Value**: Instant professional invoicing for small traders.

## 2. WhatsApp Command: "Send Report" (Module C)
- **Goal**: Allow users to trigger GST report generation on-demand.
- **Workflow**:
    - User sends command: `Report Feb 2026`.
    - System aggregates all ledger rows for the specified month.
    - System generates a GSTR-1 compliant CSV/JSON.
    - System delivers the file via WhatsApp.
- **Value**: One-tap compliance.

## 3. Voice Note Processing (OpenAI Whisper)
- **Goal**: Frictionless data entry via audio.
- **Workflow**:
    - User sends a voice note (e.g., "Sold items worth 500").
    - System downloads audio and uses OpenAI Whisper for transcription.
    - System processes text via GPT-4o-mini.
    - System updates the ledger.
- **Value**: Accessibility for busy or non-technical shop owners.

## 4. User Profile & Business Settings
- **Goal**: Personalize AI extraction and invoice generation.
- **Features**:
    - Set Default Business State (for CGST/SGST vs IGST logic).
    - Store Business GSTIN (for recipient verification).
    - Customize Invoice Templates (Logos, Headers).
- **Value**: Improved accuracy and branding.

## 5. Subscription & Payment Integration
- **Goal**: Monetize the platform.
- **Features**:
    - Stripe/Razorpay integration in the Dashboard.
    - Tiered access (Free Trial vs. Pro).
    - Automatic usage tracking and billing.
- **Value**: SaaS sustainability.
