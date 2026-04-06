# Bookkeeper → Google Cloud Run Deployment Guide (Windows)

This guide is customized for your repo structure and existing GCP project.

## Project
- **GCP Project ID:** `help-u-488511`
- **Recommended region:** `asia-south1`

## Repo structure used by this guide

```text
bookkeeper/
├── Dockerfile                  # Backend Dockerfile
├── requirements.txt
├── alembic.ini
├── alembic/
├── src/
│   ├── main.py                 # FastAPI entrypoint
│   ├── frontend/
│   │   ├── Dockerfile          # Frontend Dockerfile
│   │   ├── package.json
│   │   └── vite.config.js
│   └── ...
└── ...
```

## What will be deployed

- **Backend Cloud Run service:** `bookkeeper-be`
- **Frontend Cloud Run service:** `bookkeeper-fe`
- **Cloud SQL PostgreSQL instance:** `helpu`
- **Backend service account:** `bookkeeper-be-sa`
- **Artifact Registry repos:** `bookkeeper-be-repo`, `bookkeeper-fe-repo`

---

# Phase 0: Before you start

Install on Windows:
- Docker Desktop
- Google Cloud CLI
- Git
- PowerShell

Login and select the correct project:

```powershell
gcloud auth login
gcloud config set project help-u-488511
gcloud config get-value project
```

Expected output:

```powershell
help-u-488511
```

---

# Phase 1: Enable required APIs

```powershell
gcloud services enable `
  run.googleapis.com `
  sqladmin.googleapis.com `
  artifactregistry.googleapis.com `
  cloudbuild.googleapis.com `
  secretmanager.googleapis.com `
  logging.googleapis.com
```

Optional, depending on your integrations:
- `drive.googleapis.com` if your backend actively calls Google Drive APIs
- `iam.googleapis.com` is commonly already enabled

---

# Phase 2: Set PowerShell variables

```powershell
$env:PROJECT_ID="help-u-488511"
$env:REGION="asia-south1"
$env:REPO_ROOT="C:\path\to\bookkeeper"
```

Replace `C:\path\to\bookkeeper` with your actual repo path.

---

# Phase 3: Create Artifact Registry repositories

```powershell
gcloud artifacts repositories create bookkeeper-be-repo `
  --repository-format=docker `
  --location=$env:REGION `
  --description="Backend Docker images"

gcloud artifacts repositories create bookkeeper-fe-repo `
  --repository-format=docker `
  --location=$env:REGION `
  --description="Frontend Docker images"
```

Configure Docker authentication:

```powershell
gcloud auth configure-docker "$env:REGION-docker.pkg.dev"
```

---

# Phase 4: Create Cloud SQL PostgreSQL



## 4.A If the database already exists and is already in use

Since you already have a production Cloud SQL instance, you can **skip creating a new instance, database, and user**.

Use these existing values instead:

```powershell
$env:INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
$env:DB_USER="postgres"
$env:DB_NAME="postgres"
```

You already have `DB_PASSWORD` in production, so do **not** create a new DB user or rotate the password unless you intentionally want to.

If `DB_PASSWORD` is not yet in Secret Manager, add it like this:

```powershell
"Success7$$" | gcloud secrets create DB_PASSWORD --data-file=-
```

If the secret already exists and you need to update it:

```powershell
"YOUR_EXISTING_PROD_DB_PASSWORD" | gcloud secrets versions add DB_PASSWORD --data-file=-
```

### Important: `google_creds.json` is **not** for database connectivity

`GOOGLE_APPLICATION_CREDENTIALS=google_creds.json` is for authenticating to Google APIs, not for connecting to Cloud SQL.  
For Cloud Run → Cloud SQL, use the **Cloud SQL connection name** plus the Cloud Run service account and `--add-cloudsql-instances`. Google’s Cloud SQL docs for Cloud Run use the instance connection name for this setup. citeturn542956search0turn542956search3

### Recommended approach on Cloud Run

Do **not** bake `google_creds.json` into the image just to connect to the database. Service account keys are a security risk if not managed carefully, and Google recommends choosing more secure alternatives whenever possible. citeturn542956search1turn542956search7

If your app still needs `google_creds.json` for Google Drive or another Google API, store the JSON in **Secret Manager** and mount it as a file in Cloud Run. Cloud Run supports mounting secrets as files. citeturn542956search2

Example secret creation:

```powershell
gcloud secrets create GOOGLE_CREDS_JSON --data-file=google_creds.json
```

Example deploy flags to mount it as a file:

```powershell
--update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest
```

Then set:

```powershell
--set-env-vars=GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

That way, your app can still use the file path, but the file is coming from Secret Manager instead of being shipped inside the container.


## 4.1 Create the instance

```powershell
gcloud sql instances create helpu `
  --database-version=POSTGRES_15 `
  --cpu=1 `
  --memory=3840MB `
  --region=$env:REGION
```

## 4.2 Create the app database

```powershell
gcloud sql databases create bookkeeper `
  --instance=helpu
```

## 4.3 Create the DB user

```powershell
gcloud sql users create postgres `
  --instance=helpu `
  --password="CHANGE_TO_A_STRONG_PASSWORD"
```

## 4.4 Save the connection name

```powershell
gcloud sql instances describe helpu --format="value(connectionName)"
```

Expected format:

```powershell
help-u-488511:asia-south1:helpu
```

Save it:

```powershell
$env:INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
```

---

# Phase 5: Create backend service account

```powershell
gcloud iam service-accounts create bookkeeper-be-sa `
  --display-name="Bookkeeper Backend Service Account"
```

Grant Cloud SQL access:

```powershell
gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member="serviceAccount:bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/cloudsql.client"
```

Grant Secret Manager access:

```powershell
gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member="serviceAccount:bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

---

# Phase 6: Create secrets

At minimum create these: these are available in .env

```powershell
"CHANGE_TO_A_STRONG_PASSWORD" | gcloud secrets create DB_PASSWORD --data-file=-
"your-jwt-secret" | gcloud secrets create JWT_SECRET --data-file=-
"your-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-
"your-google-client-id" | gcloud secrets create GOOGLE_CLIENT_ID --data-file=-
"your-google-secret" | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-
"your-metaphone number id" | gcloud secrets create META_PHONE_NUMBER_ID --data-file=-
"your-whatsapp-verify-token" | gcloud secrets create WHATSAPP_VERIFY_TOKEN --data-file=-
"your-GOOGLE-redirect-url" | gcloud secrets create GOOGLE_REDIRECT_URI --data-file=-
```

Likely additional secrets for your repo:

```powershell
"your-whatsapp-token" | gcloud secrets create WHATSAPP_TOKEN --data-file=-
"your-stripe-secret" | gcloud secrets create STRIPE_SECRET_KEY --data-file=-
```

If a secret already exists, add a new version instead:

```powershell
"4eb88192837465610293847561a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0" | gcloud secrets versions add JWT_SECRET --data-file=-
```

---

# Phase 7: Backend prep for your repo

Your FastAPI entrypoint appears to be:

```text
src/main.py
```

So the Uvicorn target is probably:

```text
src.main:app
```

## 7.1 Verify your backend runs locally

From repo root:

```powershell
cd $env:REPO_ROOT
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload
```

If that fails, fix this before Cloud Run deployment.

## 7.2 Backend Dockerfile expectation

Your backend Dockerfile is at repo root:

```text
bookkeeper/Dockerfile
```

For this repo, the Dockerfile should start the app using:

```dockerfile
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
```

## 7.3 Backend runtime dependencies to watch

Based on your repo and docs, your backend may need:
- `ffmpeg`
- `poppler-utils`
- `libpq-dev`
- build tools

A good backend Dockerfile shape is:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    poppler-utils \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
```

---

# Phase 8: Database config for backend

Set env vars like:

```powershell
DB_NAME=postgres
DB_USER=postgres
DB_HOST=/cloudsql/help-u-488511:asia-south1:helpu
```

If your code builds a SQLAlchemy URL, it will usually look like:

```text
postgresql+psycopg2://postgres:<DB_PASSWORD>@/bookkeeper?host=/cloudsql/help-u-488511:asia-south1:helpu
```

---

# Phase 9: Build and push backend image

From repo root:

```powershell
cd $env:REPO_ROOT
$env:BE_IMAGE="$env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-be-repo/bookkeeper-be:1"

docker build -t $env:BE_IMAGE -f Dockerfile .
docker push $env:BE_IMAGE
```

---

# Phase 10: Deploy backend service

```powershell
gcloud run deploy bookkeeper-be `
  --image=$env:BE_IMAGE `
  --region=$env:REGION `
  --platform=managed `
  --allow-unauthenticated `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$env:INSTANCE_CONNECTION_NAME `
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest `
  --update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest `
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$env:INSTANCE_CONNECTION_NAME,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

Get backend URL:

```powershell
$env:BACKEND_URL=gcloud run services describe bookkeeper-be --region=$env:REGION --format='value(status.url)'
$env:BACKEND_URL
```

---

# Phase 11: Run Alembic migrations

Your repo has:

```text
alembic/
alembic.ini
```

## 11.1 Create migration job

```powershell
gcloud run jobs create bookkeeper-migrate `
  --image=$env:BE_IMAGE `
  --region=$env:REGION `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$env:INSTANCE_CONNECTION_NAME `
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest `
  --command alembic `
  --args upgrade,head
```

## 11.2 Execute migration job

```powershell
gcloud run jobs execute bookkeeper-migrate --region=$env:REGION
```

---

# Phase 12: Frontend prep for your repo

Your frontend lives here:

```text
src/frontend/
```

Your frontend Dockerfile exists here:

```text
src/frontend/Dockerfile
```

## 12.1 Verify frontend runs locally

```powershell
cd "$env:REPO_ROOT\src\frontend"
npm install
npm run dev
```

## 12.2 Frontend API base URL

Search your FE code for:
- `import.meta.env.VITE_`
- `VITE_API_BASE_URL`
- `axios.create(...)`

If the variable name differs, replace it in the build command later.

## 12.3 Frontend Dockerfile expectation

Make sure `src/frontend/Dockerfile` does roughly this:

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
```

## 12.4 Required `nginx.conf`

If you use React Router, add:

```nginx
server {
    listen 8080;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }
}
```

Put it in:

```text
src/frontend/nginx.conf
```

---

# Phase 13: Build and push frontend image

From repo root:

```powershell
cd $env:REPO_ROOT
$env:FE_IMAGE="$env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:1"

docker build `
  -f src/frontend/Dockerfile `
  -t $env:FE_IMAGE `
  --build-arg VITE_API_BASE_URL=$env:BACKEND_URL `
  src/frontend

docker push $env:FE_IMAGE
```

---

# Phase 14: Deploy frontend service

```powershell
gcloud run deploy bookkeeper-fe `
  --image=$env:FE_IMAGE `
  --region=$env:REGION `
  --platform=managed `
  --allow-unauthenticated
```

Get frontend URL:

```powershell
$env:FRONTEND_URL=gcloud run services describe bookkeeper-fe --region=$env:REGION --format='value(status.url)'
$env:FRONTEND_URL
```

---

# Phase 15: Configure backend CORS

Update FastAPI CORS to allow the frontend URL, then redeploy backend:

```powershell
gcloud run deploy bookkeeper-be `
  --image=$env:BE_IMAGE `
  --region=$env:REGION `
  --platform=managed `
  --allow-unauthenticated `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:INSTANCE_CONNECTION_NAME `
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$env:INSTANCE_CONNECTION_NAME,FRONTEND_URL=$env:FRONTEND_URL `
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest `
  --update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest `
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$env:INSTANCE_CONNECTION_NAME,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

---

# Phase 16: Health checks after deployment

## Backend
Open:

```text
https://YOUR_BACKEND_URL/docs
```

Check logs:

```powershell
gcloud run services logs read bookkeeper-be --region=$env:REGION
```

## Frontend
Open:

```text
https://YOUR_FRONTEND_URL
```

Check logs:

```powershell
gcloud run services logs read bookkeeper-fe --region=$env:REGION
```

---

# Phase 17: Common repo-specific gotchas

## 1. Wrong Uvicorn import path
Because your file is `src/main.py`, use:

```text
src.main:app
```

## 2. Wrong frontend build context
Because FE is in `src/frontend`, build with:

```powershell
docker build -f src/frontend/Dockerfile src/frontend
```

## 3. Missing `nginx.conf`
Without SPA fallback, React routes may fail on refresh.

## 4. Cloud SQL config still pointing to SQLite
Make sure production uses PostgreSQL.

## 5. Google credentials file usage
Avoid baking `google_creds.json` into the image if possible.

## 6. Alembic env still reading local DB
Check `alembic/env.py` for production env variable support.

---

# Phase 18: Suggested first execution order

1. Verify backend locally with `uvicorn src.main:app --reload`
2. Verify frontend locally with `npm run dev`
3. Confirm backend Dockerfile uses `src.main:app`
4. Confirm frontend Dockerfile + `nginx.conf`
5. Enable APIs
6. Create Artifact Registry repos
7. Create Cloud SQL instance/database/user
8. Create service account + permissions
9. Create secrets
10. Build and push backend image
11. Deploy backend
12. Create and run migration job
13. Test backend `/docs`
14. Build and push frontend image with backend URL
15. Deploy frontend
16. Fix CORS if needed
17. Test full app
