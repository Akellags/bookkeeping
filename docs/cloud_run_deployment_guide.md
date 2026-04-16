# Cloud Run Deployment Guide

This guide details the steps to deploy the **Help U Bookkeeper** application (FastAPI + React) to Google Cloud Run.

## Prerequisites

1.  **Google Cloud CLI**: Installed and configured (`gcloud auth login`).
2.  **Project ID**: `help-u-488511`.
3.  **Permissions**: Ensure your account has `Cloud Run Admin` and `Service Account User` roles.

## Deployment Files

-   **Backend**: `Dockerfile` (root), `.dockerignore` (root).
-   **Frontend**: `src/frontend/Dockerfile`, `src/frontend/nginx.conf`, `src/frontend/.dockerignore`.
-   **Automation**: `devOps/deploy_all.sh`.

## Step-by-Step Process

### 1. Authenticate & Set Project
```bash
gcloud auth login
gcloud config set project help-u-488511
```

### 2. Prepare Environment
Ensure your `.env` file in the root directory contains the correct production values for:
- `INSTANCE_CONNECTION_NAME`
- `DB_USER`, `DB_PASS`, `DB_NAME`
- `OPENAI_API_KEY`
- `META_ACCESS_TOKEN`, etc.

### 3. Deploy Backend
From the project root:
```bash
gcloud run deploy help-u-backend \
  --source . \
  --region asia-south1 \
  --env-vars-file .env \
  --allow-unauthenticated
```
*Note: Copy the **Service URL** from the output.*

### 4. Configure Frontend
Update your React application to use the Backend Service URL for API calls.

### 5. Deploy Frontend (Firebase)
The frontend is deployed to Firebase Hosting.
```bash
cd src/frontend
# Set environment variables for build
export VITE_API_BASE_URL="https://bookkeeper-be-486079244466.asia-south1.run.app"
npm install
npm run build
cd ../..
firebase deploy --only hosting
```

## Automated Deployment
Use the provided script to deploy both services at once:
```bash
bash devOps/deploy_all.sh
```

## Post-Deployment Checklist
1.  **IAM**: Ensure the default compute service account has the **Cloud SQL Client** role.
2.  **Domain**: Configure Custom Domains in the Cloud Run console if needed.
3.  **Secrets**: For production security, migrate sensitive `.env` variables to **Google Secret Manager**.
