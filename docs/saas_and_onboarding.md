# SaaS Strategy & User Onboarding

## 1. User Onboarding Flow (ReactJS Frontend)
To securely onboard users and manage their subscriptions, a central web portal is required.

### Step 1: Sign-up & Profile
- User logs in via **Google OAuth2** (ensures email matches their primary Drive account).
- User enters their **WhatsApp Phone Number** (verified via OTP if necessary).

### Step 2: Google Drive Authorization
- App requests permission for the `https://www.googleapis.com/auth/drive.file` scope.
- This creates an isolated space in the user's Drive for "Help U" files.
- **Refresh Token** is stored securely in the app's metadata database (Supabase/PostgreSQL).

### Step 3: Meta WhatsApp Opt-in
- User is directed to a "Start on WhatsApp" button (wa.me link with a unique identifier).
- This links the WhatsApp session to their Google account and subscription.

## 2. SaaS Model (Subscription-based)
### Tiers (Example)
- **Basic**: Up to 50 bills/month, Standard GST reports.
- **Pro**: Unlimited bills, Voice support, Priority support, Multiple HSN mapping.
- **Enterprise**: Custom templates, Team access.

### Payment Integration
- **Gateway**: Stripe or Razorpay.
- **Billing Cycle**: Monthly or Yearly.
- **Trial**: 7-day free trial (up to 10 bills) to test AI accuracy.

### Subscription Verification Logic
- Every incoming WhatsApp message checks the user's subscription status in the metadata database.
- If expired, the bot sends a polite renewal link.

## 3. Tech Stack for SaaS
- **Portal**: ReactJS + Tailwind CSS.
- **Backend**: Python (FastAPI/Flask) or Node.js.
- **Auth**: Supabase Auth or Auth0.
- **Database**: Supabase PostgreSQL (Stores UserID, WhatsAppID, Google Token, Sub Status).
- **Billing**: Stripe Billing / Webhooks.
