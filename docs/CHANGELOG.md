# Changelog

All notable changes to the **Help U Bookkeeper** project will be documented in this file.

## [2026-04-22] - Latency Optimization & Gemini-First Architecture

### Added
- **Gemini-First Extraction**: Fully transitioned to **Gemini 2.5 Flash** for multimodal invoice extraction, replacing the slower 2-step Document AI process.
- **Asynchronous Task Decoupling**: Backgrounded non-critical tasks (Google Drive uploads and Google Doc generation) to provide near-instant chat confirmations (~3s response).
- **Smart Image Compression**: Implemented automatic resizing and optimization for large invoice images in `src/utils.py` to reduce bandwidth and latency.
- **Regional Optimization**: Aligned Vertex AI infrastructure to `asia-south1` (Mumbai) to match the backend Cloud Run region, eliminating cross-region network overhead.

### Fixed
- **WhatsApp Webhook Stability**: Resolved Meta Graph API version mismatches (updated to v21) and fixed token/ID stripping issues for reliable live mode operation.
- **Place of Supply Logic**: Corrected the automatic extraction of State Codes from GSTINs for accurate IGST vs CGST/SGST calculations.
- **OAuth & Secret Management**: Standardized Meta/WhatsApp secret handling and updated deployment guides in `gcp_env_vars.md`.

### Changed
- **Extraction Pipeline**: 90% reduction in end-to-end extraction latency (from ~75s to ~12s) via 1-step multimodal processing.
- **Backend Deployment Reference**: Updated `docs/gcp_env_vars.md` to include Firebase-specific frontend deployment and consolidated secret management commands.

## [2026-04-13] - Onboarding & Login Optimization (Current Sprint)

### Added
- **Dynamic Business Onboarding**: Users can now provide their **Legal Business Name** and **GSTIN** during the signup/onboarding process.
- **Instant Login Flow**: Implemented a "silent" login path for returning users. Users with complete profiles bypass onboarding/success screens and land directly on the dashboard.
- **LoginSuccess Page**: Added a dedicated frontend route `/login-success` to handle token persistence and seamless redirection.
- **BusinessOnboarding Page**: A new frontend page to capture business identity, with logic to differentiate between "New Setup" and "Profile Update".
- **Firebase Hosting Support**: Added `firebase.json` and `.firebaserc` for deploying the frontend to Firebase Hosting, enabling custom domain support (`books.helpsu.ai`).
- **Profile Incomplete Banner**: Added a high-visibility alert on the Dashboard to guide users with legacy/default business details to update their settings.

### Fixed
- **Session Stability**: Resolved a critical bug where `refresh_token` was lost (overwritten with `None`) during silent re-authentications.
- **PKCE "Missing code verifier"**: Switched to a manual `requests.post` token exchange in the backend for more reliable stateless OAuth handling.
- **Redirect Loop**: Fixed a 401 Unauthorized loop caused by secret key mismatches between backend environment variables and Google Secret Manager.
- **Independent UI Scrolling**: Optimized the GST Reports table to support internal scrolling, preventing the navigation sidebar from being pushed off-screen.

### Changed
- **Backend Redirect Logic**: Updated `auth.py` to intelligently route users to `/onboarding-business` or `/login-success` based on their profile status.
- **OAuth Scopes**: Expanded requested permissions to include `https://www.googleapis.com/auth/documents` for automated invoice template generation.
- **Google Drive Naming**: Refined the folder structure to use "Help U - [Business Name]" as the root identifier in the user's Drive.

### Infrastructure
- **Custom Domain**: Configured `books.helpsu.ai` via Firebase Hosting, connected to the Cloud Run backend via Hosting rewrites.
- **Environment Management**: Updated `gcp_env_vars.md` with consolidated deployment commands for the new Firebase + Cloud Run architecture.
