# GCP Environment Variables for PowerShell

To restore your deployment environment after a restart, copy and paste these commands into your **PowerShell** window:

```powershell
# Project Configuration
$env:PROJECT_ID="help-u-488511"
$env:REGION="asia-south1"
$env:REPO_ROOT="c:\Users\ALIENWARE\Projects\helpU\bookkeeper"

# Service and Database Configuration
$env:INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
$env:BACKEND_URL="https://bookkeeper-be-486079244466.asia-south1.run.app"
$env:FRONTEND_URL="https://bookkeeper-fe-486079244466.asia-south1.run.app"

# Verify they are set
echo "Project: $env:PROJECT_ID"
echo "Region: $env:REGION"
echo "Backend: $env:BACKEND_URL"
echo "Frontend: $env:FRONTEND_URL"
```

## Deployment Commands Reference

### 1. FASTEST Backend Deploy (Builds on Cloud)
Recommended method—takes ~2 mins and ensures latest code is deployed without local push overhead.
```powershell
gcloud run deploy bookkeeper-be `
  --source . `
  --region=$env:REGION `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --allow-unauthenticated `
  --set-secrets="DB_PASS=DB_PASSWORD:latest,SECRET_KEY=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest" `
  --set-env-vars="ENV=production,DB_NAME=postgres,DB_USER=postgres,INSTANCE_CONNECTION_NAME=$env:INSTANCE_CONNECTION_NAME,FRONTEND_URL=$env:FRONTEND_URL,GOOGLE_REDIRECT_URI=$env:BACKEND_URL/auth/callback,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json"
```

### 2. Full Backend Deploy (With WhatsApp)
Once WhatsApp keys are ready, add them to the command:
```powershell
gcloud run deploy bookkeeper-be `
  --source . `
  --region=$env:REGION `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --allow-unauthenticated `
  --set-secrets="DB_PASS=DB_PASSWORD:latest,SECRET_KEY=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,META_ACCESS_TOKEN=WHATSAPP_TOKEN:latest,META_PHONE_NUMBER_ID=META_PHONE_NUMBER_ID:latest,WHATSAPP_VERIFY_TOKEN=WHATSAPP_VERIFY_TOKEN:latest,/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest" `
  --set-env-vars="ENV=production,DB_NAME=postgres,DB_USER=postgres,INSTANCE_CONNECTION_NAME=$env:INSTANCE_CONNECTION_NAME,FRONTEND_URL=$env:FRONTEND_URL,GOOGLE_REDIRECT_URI=$env:BACKEND_URL/auth/callback,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json"
```

### 3. Frontend Deploy (FASTEST - Builds on Cloud)
Recommended method—takes ~2 mins.
```powershell
cd src/frontend
gcloud run deploy bookkeeper-fe `
  --source . `
  --region=$env:REGION `
  --allow-unauthenticated `
  --set-build-env-vars="VITE_API_BASE_URL=$env:BACKEND_URL"
```

### 4. Frontend Deploy (Local Docker Method)
Use this if you prefer building locally and pushing to registry.
```powershell
cd src/frontend
docker build `
  -f Dockerfile `
  -t $env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:latest `
  --build-arg VITE_API_BASE_URL=$env:BACKEND_URL `
  .
docker push $env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:latest

gcloud run deploy bookkeeper-fe `
  --image=$env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:latest `
  --region=$env:REGION `
  --allow-unauthenticated
```
