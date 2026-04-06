# Google Cloud Run Deployment Guide (Ubuntu)

## Project
- Project ID: help-u-488511

---

## Phase 1: Setup

```bash
sudo apt update
sudo apt install -y docker.io git curl

# Install gcloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

gcloud init
gcloud config set project help-u-488511
```

---

## Phase 2: Enable APIs

```bash
gcloud services enable   run.googleapis.com   sqladmin.googleapis.com   artifactregistry.googleapis.com   cloudbuild.googleapis.com   secretmanager.googleapis.com   logging.googleapis.com
```

---

## Phase 3: Set variables

```bash
export PROJECT_ID="help-u-488511"
export REGION="us-central1"
```

---

## Phase 4: Artifact Registry

```bash
gcloud artifacts repositories create bookkeeper-be-repo   --repository-format=docker   --location=$REGION

gcloud artifacts repositories create bookkeeper-fe-repo   --repository-format=docker   --location=$REGION

gcloud auth configure-docker $REGION-docker.pkg.dev
```

---

## Phase 5: Cloud SQL

```bash
gcloud sql instances create bookkeeper-db   --database-version=POSTGRES_15   --cpu=1   --memory=3840MB   --region=$REGION

gcloud sql databases create bookkeeper --instance=bookkeeper-db

gcloud sql users create bookkeeper_user   --instance=bookkeeper-db   --password='CHANGE_PASSWORD'
```

---

## Phase 6: Service Account

```bash
gcloud iam service-accounts create bookkeeper-be-sa

gcloud projects add-iam-policy-binding $PROJECT_ID   --member="serviceAccount:bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com"   --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID   --member="serviceAccount:bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com"   --role="roles/secretmanager.secretAccessor"
```

---

## Phase 7: Secrets

```bash
printf 'password' | gcloud secrets create DB_PASSWORD --data-file=-
printf 'jwt-secret' | gcloud secrets create JWT_SECRET --data-file=-
printf 'openai-key' | gcloud secrets create OPENAI_API_KEY --data-file=-
```

---

## Phase 8: Backend Deploy

```bash
export BE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-be-repo/bookkeeper-be:1"

docker build -t $BE_IMAGE .
docker push $BE_IMAGE

gcloud run deploy bookkeeper-be   --image=$BE_IMAGE   --region=$REGION   --platform=managed   --allow-unauthenticated   --service-account=bookkeeper-be-sa@$PROJECT_ID.iam.gserviceaccount.com   --add-cloudsql-instances=$PROJECT_ID:$REGION:bookkeeper-db   --set-env-vars=DB_NAME=bookkeeper,DB_USER=bookkeeper_user,DB_HOST=/cloudsql/$PROJECT_ID:$REGION:bookkeeper-db   --set-secrets=DB_PASSWORD=DB_PASSWORD:latest
```

---

## Phase 9: Frontend Deploy

```bash
export FE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/bookkeeper-fe-repo/bookkeeper-fe:1"

docker build -t $FE_IMAGE .
docker push $FE_IMAGE

gcloud run deploy bookkeeper-fe   --image=$FE_IMAGE   --region=$REGION   --platform=managed   --allow-unauthenticated
```

---

## Done
