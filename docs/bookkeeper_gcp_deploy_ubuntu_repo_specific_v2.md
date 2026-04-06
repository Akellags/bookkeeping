# Bookkeeper → Google Cloud Run Deployment Guide (Ubuntu)

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

From Ubuntu, install the tools you need:

```bash
sudo apt update
sudo apt install -y git curl docker.io ca-certificates gnupg
sudo usermod -aG docker $USER
newgrp docker
```

Install Google Cloud CLI:

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

Login and select the correct project:

```bash
gcloud auth login
gcloud config set project help-u-488511
gcloud config get-value project
```

Expected output:

```bash
help-u-488511
```

---

# Phase 1: Enable required APIs

These are the APIs you need for this deployment flow:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com
```

Optional, depending on your integrations:
- `drive.googleapis.com` if your backend actively calls Google Drive APIs
- `iam.googleapis.com` is commonly already enabled

---

# Phase 2: Set shell variables

```bash
export PROJECT_ID="help-u-488511"
export REGION="asia-south1"
export REPO_ROOT="$HOME/bookkeeper"
```

Change `REPO_ROOT` if your repo is somewhere else.

---

# Phase 3: Create Artifact Registry repositories

```bash
gcloud artifacts repositories create bookkeeper-be-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Backend Docker images"

gcloud artifacts repositories create bookkeeper-fe-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Frontend Docker images"
```

Configure Docker authentication:

```bash
gcloud auth configure-docker $REGION-docker.pkg.dev
```

---

# Phase 4: Create Cloud SQL PostgreSQL



## 4.A If the database already exists and is already in use

Since you already have a production Cloud SQL instance, you can **skip creating a new instance, database, and user**.

Use these existing values instead:

```bash
export INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
export DB_USER="postgres"
export DB_NAME="postgres"
```

You already have `DB_PASSWORD` in production, so do **not** create a new DB user or rotate the password unless you intentionally want to.

If `DB_PASSWORD` is not yet in Secret Manager, add it like this:

```bash
printf 'YOUR_EXISTING_PROD_DB_PASSWORD' | gcloud secrets create DB_PASSWORD --data-file=-
```

If the secret already exists and you need to update it:

```bash
printf 'YOUR_EXISTING_PROD_DB_PASSWORD' | gcloud secrets versions add DB_PASSWORD --data-file=-
```

### Important: `google_creds.json` is **not** for database connectivity

`GOOGLE_APPLICATION_CREDENTIALS=google_creds.json` is for authenticating to Google APIs, not for connecting to Cloud SQL.  
For Cloud Run → Cloud SQL, use the **Cloud SQL connection name** plus the Cloud Run service account and `--add-cloudsql-instances`. Google’s Cloud SQL docs for Cloud Run use the instance connection name for this setup. citeturn542956search0turn542956search3

### Recommended approach on Cloud Run

Do **not** bake `google_creds.json` into the image just to connect to the database. Service account keys are a security risk if not managed carefully, and Google recommends choosing more secure alternatives whenever possible. citeturn542956search1turn542956search7

If your app still needs `google_creds.json` for Google Drive or another Google API, store the JSON in **Secret Manager** and mount it as a file in Cloud Run. Cloud Run supports mounting secrets as files. citeturn542956search2

Example secret creation:

```bash
gcloud secrets create GOOGLE_CREDS_JSON --data-file=google_creds.json
```

Example deploy flags to mount it as a file:

```bash
--update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest
```

Then set:

```bash
--set-env-vars=GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

That way, your app can still use the file path, but the file is coming from Secret Manager instead of being shipped inside the container.


## 4.1 Create the instance

```bash
gcloud sql instances create helpu \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MB \
  --region=$REGION
```

## 4.2 Create the app database

```bash
gcloud sql databases create bookkeeper \
  --instance=helpu
```

## 4.3 Create the DB user

```bash
gcloud sql users create postgres \
  --instance=helpu \
  --password='CHANGE_TO_A_STRONG_PASSWORD'
```

## 4.4 Save the connection name

```bash
gcloud sql instances describe helpu \
  --format="value(connectionName)"
```

Expected format:

```bash
help-u-488511:asia-south1:helpu
```

Save it:

```bash
export INSTANCE_CONNECTION_NAME="help-u-488511:asia-south1:helpu"
```

---

# Phase 5: Create backend service account

```bash
gcloud iam service-accounts create bookkeeper-be-sa \
  --display-name="Bookkeeper Backend Service Account"
```

Grant Cloud SQL access:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

Grant Secret Manager access:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

If your backend uses Google Drive via service account / ADC, also grant only the minimum extra permissions it really needs.

---

# Phase 6: Create secrets

At minimum create these:

```bash
printf 'CHANGE_TO_A_STRONG_PASSWORD' | gcloud secrets create DB_PASSWORD --data-file=-
printf 'your-jwt-secret' | gcloud secrets create JWT_SECRET --data-file=-
printf 'your-openai-key' | gcloud secrets create OPENAI_API_KEY --data-file=-
printf 'your-google-client-id' | gcloud secrets create GOOGLE_CLIENT_ID --data-file=-
printf 'your-google-client-secret' | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-
```

Likely additional secrets for your repo:

```bash
printf 'your-whatsapp-token' | gcloud secrets create WHATSAPP_TOKEN --data-file=-
printf 'your-stripe-secret' | gcloud secrets create STRIPE_SECRET_KEY --data-file=-
```

If a secret already exists, add a new version instead of creating again:

```bash
printf 'new-value' | gcloud secrets versions add JWT_SECRET --data-file=-
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

```bash
cd $REPO_ROOT
python3 -m venv .venv
source .venv/bin/activate
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

Make sure it does **not** use `main:app` unless your file is really at root.

## 7.3 Backend runtime dependencies to watch

Based on your repo and docs, your backend may need these system packages:
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

Your backend uses Alembic and PostgreSQL in production.

For Cloud Run + Cloud SQL, set env vars like:

```bash
DB_NAME=postgres
DB_USER=postgres
DB_HOST=/cloudsql/help-u-488511:asia-south1:helpu
```

If your code builds a SQLAlchemy URL, it will usually look like:

```text
postgresql+psycopg2://postgres:<DB_PASSWORD>@/bookkeeper?host=/cloudsql/help-u-488511:asia-south1:helpu
```

If your code currently expects SQLite by default, make sure production switches to PostgreSQL when these env vars are present.

---

# Phase 9: Build and push backend image

From repo root:

```bash
cd $REPO_ROOT
export BE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-be-repo/bookkeeper-be:1"

docker build -t $BE_IMAGE -f Dockerfile .
docker push $BE_IMAGE
```

---

# Phase 10: Deploy backend service

Start with a broad secret/env set, then trim later after it works.

```bash
gcloud run deploy bookkeeper-be \
  --image=$BE_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME \
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest \
  --update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

Get backend URL:

```bash
gcloud run services describe bookkeeper-be \
  --region=$REGION \
  --format='value(status.url)'
```

Save it:

```bash
export BACKEND_URL="$(gcloud run services describe bookkeeper-be --region=$REGION --format='value(status.url)')"
echo $BACKEND_URL
```

---

# Phase 11: Run Alembic migrations

Your repo has:

```text
alembic/
alembic.ini
```

That means migration support is already present.

## 11.1 Create a Cloud Run job for migrations

```bash
gcloud run jobs create bookkeeper-migrate \
  --image=$BE_IMAGE \
  --region=$REGION \
  --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME \
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest \
  --command alembic \
  --args upgrade,head
```

## 11.2 Execute the migration job

```bash
gcloud run jobs execute bookkeeper-migrate --region=$REGION
```

## 11.3 If the job already exists and you changed the image

```bash
gcloud run jobs update bookkeeper-migrate \
  --image=$BE_IMAGE \
  --region=$REGION \
  --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME \
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest
```

---

# Phase 12: Frontend prep for your repo

Your frontend lives here:

```text
src/frontend/
```

Your frontend Dockerfile already exists here:

```text
src/frontend/Dockerfile
```

## 12.1 Verify frontend runs locally

```bash
cd $REPO_ROOT/src/frontend
npm install
npm run dev
```

## 12.2 Frontend API base URL

Because this is Vite, the backend URL is usually passed with:

```text
VITE_API_BASE_URL
```

Search your frontend code for:
- `import.meta.env.VITE_`
- `VITE_API_BASE_URL`
- `axios.create(...)`

If the frontend uses a different env variable name, replace it in the build command below.

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

If you use React Router, you need SPA fallback:

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

Place this file in:

```text
src/frontend/nginx.conf
```

and make sure the Dockerfile copies it.

---

# Phase 13: Build and push frontend image

From repo root:

```bash
cd $REPO_ROOT
export FE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:1"

docker build \
  -f src/frontend/Dockerfile \
  -t $FE_IMAGE \
  --build-arg VITE_API_BASE_URL=$BACKEND_URL \
  src/frontend

docker push $FE_IMAGE
```

---

# Phase 14: Deploy frontend service

```bash
gcloud run deploy bookkeeper-fe \
  --image=$FE_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated
```

Get frontend URL:

```bash
export FRONTEND_URL="$(gcloud run services describe bookkeeper-fe --region=$REGION --format='value(status.url)')"
echo $FRONTEND_URL
```

---

# Phase 15: Configure backend CORS

Your backend likely needs to allow the frontend Cloud Run URL.

In FastAPI, configure:

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "https://your-frontend-url.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then redeploy backend with the frontend URL passed in:

```bash
gcloud run deploy bookkeeper-be \
  --image=$BE_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME,FRONTEND_URL=$FRONTEND_URL \
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest \
  --update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

---

# Phase 16: Health checks after deployment

## Backend
Open:

```text
https://YOUR_BACKEND_URL/docs
```

Check logs:

```bash
gcloud run services logs read bookkeeper-be --region=$REGION
```

## Frontend
Open:

```text
https://YOUR_FRONTEND_URL
```

Check frontend logs:

```bash
gcloud run services logs read bookkeeper-fe --region=$REGION
```

---

# Phase 17: Common repo-specific gotchas

## 1. Wrong Uvicorn import path
Because your file is `src/main.py`, use:

```text
src.main:app
```

not `main:app`.

## 2. Wrong frontend Docker build context
Because FE is in `src/frontend`, use:

```bash
docker build -f src/frontend/Dockerfile src/frontend
```

not repo root unless the Dockerfile is written for that.

## 3. Missing `nginx.conf`
Without SPA fallback, refresh on nested React routes will break.

## 4. Cloud SQL config still pointing to SQLite
Make sure production code switches off SQLite.

## 5. Google credentials file usage
Avoid baking `google_creds.json` into the image if possible. Prefer Cloud Run service account and Secret Manager.

## 6. Alembic env still reading local DB
Check `alembic/env.py` so it uses production env vars on Cloud Run.

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

---

# Phase 19: Exact commands summary

## Backend build
```bash
cd $REPO_ROOT
export BE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-be-repo/bookkeeper-be:1"
docker build -t $BE_IMAGE -f Dockerfile .
docker push $BE_IMAGE
```

## Backend deploy
```bash
gcloud run deploy bookkeeper-be \
  --image=$BE_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME \
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest,JWT_SECRET=JWT_SECRET:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,WHATSAPP_TOKEN=WHATSAPP_TOKEN:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest \
  --update-secrets=/secrets/google/google_creds.json=GOOGLE_CREDS_JSON:latest \
  --set-env-vars=ENV=production,DB_NAME=postgres,DB_USER=postgres,DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/google_creds.json
```

## Frontend build
```bash
cd $REPO_ROOT
export FE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:1"
docker build -f src/frontend/Dockerfile -t $FE_IMAGE --build-arg VITE_API_BASE_URL=$BACKEND_URL src/frontend
docker push $FE_IMAGE
```

## Frontend deploy
```bash
gcloud run deploy bookkeeper-fe \
  --image=$FE_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated
```
