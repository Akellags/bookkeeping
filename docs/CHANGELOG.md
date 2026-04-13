# Changelog

All notable changes to the **Help U Bookkeeper** project will be documented in this file.

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
