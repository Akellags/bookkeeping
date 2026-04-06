# Google Cloud Run Deployment Guide (Windows)

## Prerequisites
- Install Docker Desktop
- Install Google Cloud SDK
- Use PowerShell or Git Bash

---

## Phase 1: Setup

```powershell
gcloud auth login
gcloud config set project help-u-488511
```

---

## Phase 2: Enable APIs

```powershell
gcloud services enable run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com logging.googleapis.com
```

---

## Phase 3: Variables

```powershell
$env:PROJECT_ID="help-u-488511"
$env:REGION="us-central1"
```

---

## Phase 4: Artifact Registry

```powershell
gcloud artifacts repositories create bookkeeper-be-repo --repository-format=docker --location=$env:REGION
gcloud artifacts repositories create bookkeeper-fe-repo --repository-format=docker --location=$env:REGION

gcloud auth configure-docker $env:REGION-docker.pkg.dev
```

---

## Phase 5: Cloud SQL

```powershell
gcloud sql instances create bookkeeper-db --database-version=POSTGRES_15 --cpu=1 --memory=3840MB --region=$env:REGION

gcloud sql databases create bookkeeper --instance=bookkeeper-db

gcloud sql users create bookkeeper_user --instance=bookkeeper-db --password="CHANGE_PASSWORD"
```

---

## Phase 6: Service Account

```powershell
gcloud iam service-accounts create bookkeeper-be-sa

gcloud projects add-iam-policy-binding $env:PROJECT_ID --member="serviceAccount:bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com" --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $env:PROJECT_ID --member="serviceAccount:bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

---

## Phase 7: Secrets

```powershell
echo password | gcloud secrets create DB_PASSWORD --data-file=-
echo jwt-secret | gcloud secrets create JWT_SECRET --data-file=-
echo openai-key | gcloud secrets create OPENAI_API_KEY --data-file=-
```

---

## Phase 8: Backend Deploy

```powershell
$BE_IMAGE="$env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-be-repo/bookkeeper-be:1"

docker build -t $BE_IMAGE .
docker push $BE_IMAGE

gcloud run deploy bookkeeper-be `
  --image=$BE_IMAGE `
  --region=$env:REGION `
  --platform=managed `
  --allow-unauthenticated `
  --service-account=bookkeeper-be-sa@$env:PROJECT_ID.iam.gserviceaccount.com `
  --add-cloudsql-instances=$env:PROJECT_ID:$env:REGION:bookkeeper-db `
  --set-env-vars=DB_NAME=bookkeeper,DB_USER=bookkeeper_user,DB_HOST=/cloudsql/$env:PROJECT_ID:$env:REGION:bookkeeper-db `
  --set-secrets=DB_PASSWORD=DB_PASSWORD:latest
```

---

## Phase 9: Frontend Deploy

```powershell
$FE_IMAGE="$env:REGION-docker.pkg.dev/$env:PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:1"

docker build -t $FE_IMAGE .
docker push $FE_IMAGE

gcloud run deploy bookkeeper-fe `
  --image=$FE_IMAGE `
  --region=$env:REGION `
  --platform=managed `
  --allow-unauthenticated
```

---

## Done
