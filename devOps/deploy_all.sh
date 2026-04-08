#!/bin/bash

# Configuration
PROJECT_ID="help-u-488511"
REGION="asia-south1"
BACKEND_SERVICE="help-u-backend"
FRONTEND_SERVICE="help-u-frontend"

# Set project
gcloud config set project $PROJECT_ID

echo "🚀 Starting Deployment to Cloud Run..."

# 1. Deploy Backend
echo "📦 Deploying Backend ($BACKEND_SERVICE)..."
gcloud run deploy $BACKEND_SERVICE \
  --source . \
  --region $REGION \
  --env-vars-file .env.production \
  --allow-unauthenticated \
  --service-account="895750056952-compute@developer.gserviceaccount.com" # Update if needed

# 2. Get Backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# 3. Update Frontend API URL (if applicable)
# For Vite, you might need to rebuild the frontend with the backend URL
# cd src/frontend
# echo "VITE_API_URL=$BACKEND_URL" > .env.production

# 4. Deploy Frontend
echo "📦 Deploying Frontend ($FRONTEND_SERVICE)..."
cd src/frontend
gcloud run deploy $FRONTEND_SERVICE \
  --source . \
  --region $REGION \
  --allow-unauthenticated

echo "🎉 Deployment Complete!"
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format='value(status.url)')
echo "🔗 Frontend URL: $FRONTEND_URL"
echo "🔗 Backend URL: $BACKEND_URL"
