# GCP Environment Variables for PowerShell

To restore your deployment environment after a restart, copy and paste these commands into your **PowerShell** window. 

**CRITICAL**: You MUST run these from the project root directory: `c:\Users\ALIENWARE\Projects\helpU\bookkeeper`

```powershell
# 0. Go to Project Root
cd "c:\Users\ALIENWARE\Projects\helpU\bookkeeper"

# 1. Project Configuration
$env:PROJECT_ID="help-u-488511"
$env:REGION="asia-south1"
$env:REPO_ROOT="c:\Users\ALIENWARE\Projects\helpU\bookkeeper"

# Service and Database Configuration
$env:INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
$env:BACKEND_URL="https://bookkeeper-be-486079244466.asia-south1.run.app"
$env:FRONTEND_URL="https://books.helpsu.ai"

# Verify they are set
echo "Project: $env:PROJECT_ID"
echo "Region: $env:REGION"
echo "Backend: $env:BACKEND_URL"
echo "Frontend: $env:FRONTEND_URL"
```

## Deployment Commands Reference

### 1. Final Backend Deploy (Cloud Run)
Full deployment including WhatsApp.
```powershell
gcloud run deploy bookkeeper-be `
  --source . `
  --region=$env:REGION `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --allow-unauthenticated `
  --command="uvicorn" `
  --args="src.main:app,--host,0.0.0.0,--port,8080" `
  --set-secrets="DB_PASS=DB_PASSWORD:latest,SECRET_KEY=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,META_ACCESS_TOKEN=META_ACCESS_TOKEN:latest,META_PHONE_NUMBER_ID=META_PHONE_NUMBER_ID:latest,WHATSAPP_VERIFY_TOKEN=WHATSAPP_VERIFY_TOKEN:latest,/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest" `
  --set-env-vars="ENV=production,DB_NAME=postgres,DB_USER=postgres,INSTANCE_CONNECTION_NAME=$env:INSTANCE_CONNECTION_NAME,FRONTEND_URL=$env:FRONTEND_URL,GOOGLE_REDIRECT_URI=$env:BACKEND_URL/auth/callback,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json,GOOGLE_CLOUD_PROJECT=$env:PROJECT_ID,DOCUMENT_AI_LOCATION=us,DOCUMENT_AI_PROCESSOR_ID=7e43aab74a60ef04,VERTEX_AI_LOCATION=asia-south1,VERTEX_AI_MODEL=gemini-2.5-flash,DEFAULT_EXTRACTION_PROVIDER=google,ENABLE_OPENAI_FALLBACK=true"
```

### 1b. Minimal Backend Deploy (No WhatsApp)
Use this for testing Google Extraction without WhatsApp overhead.
```powershell
gcloud run deploy bookkeeper-be `
  --source . `
  --region=$env:REGION `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --allow-unauthenticated `
  --command="uvicorn" `
  --args="src.main:app,--host,0.0.0.0,--port,8080" `
  --set-secrets="DB_PASS=DB_PASSWORD:latest,SECRET_KEY=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest" `
  --set-env-vars="ENV=production,DB_NAME=postgres,DB_USER=postgres,INSTANCE_CONNECTION_NAME=$env:INSTANCE_CONNECTION_NAME,FRONTEND_URL=$env:FRONTEND_URL,GOOGLE_REDIRECT_URI=$env:BACKEND_URL/auth/callback,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json,GOOGLE_CLOUD_PROJECT=$env:PROJECT_ID,DOCUMENT_AI_LOCATION=us,DOCUMENT_AI_PROCESSOR_ID=7e43aab74a60ef04,VERTEX_AI_LOCATION=asia-south1,VERTEX_AI_MODEL=gemini-2.5-flash,DEFAULT_EXTRACTION_PROVIDER=google,ENABLE_OPENAI_FALLBACK=true"
```

### 2. Frontend Deploy (Firebase)
Frontend is ONLY deployed to Firebase. 
```powershell
# 1. Set the Backend Environment Variable (if not already set)
$env:VITE_API_BASE_URL="https://bookkeeper-be-486079244466.asia-south1.run.app"

# 2. Build and Deploy
cd src/frontend
npm install
npm run build
cd ../..
firebase deploy --only hosting
```
