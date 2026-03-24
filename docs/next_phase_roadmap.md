# Help U - Next Phase Roadmap

This document outlines the planned improvements and new features for the next phase of development, building upon the secure onboarding and reliability features implemented in Phase 1.

## 1. Security & Compliance
- **Secret Management**: Move `SECRET_KEY`, `META_ACCESS_TOKEN`, and `GOOGLE_CLIENT_SECRET` from `.env` files to a managed secret store (e.g., AWS Secrets Manager, HashiCorp Vault).
- **JWT Secret Rotation**: Implement a mechanism to rotate the `SECRET_KEY` used for OAuth state signing and authentication tokens.
- **Enhanced Token Entropy**: Increase the length of the WhatsApp Magic Link handover token for enhanced security in production environments.
- **Audit Logging**: Implement comprehensive audit logs for all security-sensitive actions (e.g., Google account linking, business profile changes).

## 2. Onboarding Optimization
- **Real-time Notifications**: Implement a WebSocket-based notification system to alert web users immediately when their WhatsApp account is successfully linked.
- **Conversion Tracking**: Build an internal dashboard to monitor the onboarding funnel: `Web Visit -> Google OAuth -> WhatsApp Handover Success`.
- **Simplified Onboarding**: Research and implement "One-Click" Google Drive setup where possible to further reduce friction.

## 3. Core Feature Enhancements
- **Billing & Subscriptions**: Finalize the Stripe integration, including webhook handling for subscription lifecycle events (renewals, cancellations).
- **Advanced AI Extraction**: Fine-tune the AI processing model to improve extraction accuracy for complex, multi-item invoices.
- **Multi-Business Dashboard**: Enhance the frontend to support seamless switching between multiple business profiles with distinct ledger sheets.
- **Bulk Export**: Implement bulk export of transactions from Google Sheets to other accounting formats (e.g., CSV, Tally-compatible XML).

## 4. Reliability & Performance
- **Database Migrations**: Adopt a formal migration tool (e.g., Alembic) to manage database schema changes across development and production environments.
- **Performance Monitoring**: Integrate an APM tool (e.g., Sentry, New Relic) to track API latency and errors in real-time.
- **Improved Caching**: Implement caching for frequently accessed business profile data to reduce database load.

## 5. Mobile & Bot Improvements
- **Interactive Voice Responses (IVR)**: Explore adding voice-based commands for recording sales directly on WhatsApp via audio messages.
- **Quick Actions**: Add WhatsApp "Quick Reply" buttons for common tasks like "Get Monthly Summary" or "Download Last Invoice".
