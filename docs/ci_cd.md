when ever there is a change to the **backend code**, you need to rebuild and redeploy the backend service.

1.  **Rebuild Backend Image**:
    ```powershell
    docker build -t $env:BE_IMAGE -f Dockerfile .
    ```

2.  **Push and Redeploy**:
    ```powershell
    docker push $env:BE_IMAGE
    gcloud run deploy bookkeeper-be --image=$env:BE_IMAGE --region=asia-south1

    docker image prune -f

    ```
