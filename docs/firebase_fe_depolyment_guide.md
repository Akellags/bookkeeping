The `App.jsx` setup is correctly using `VITE_API_BASE_URL` with a fallback for Cloud Run. I'll now provide the deployment steps, including the necessary command to set the backend URL during the build.

### 🚀 Step-by-Step Deployment: Frontend to Firebase

Follow these steps exactly to build your frontend and deploy it to Firebase with the correct backend connection.

#### 1. Set the Backend Environment Variable
Open your terminal (PowerShell) and set your backend URL so the frontend knows where to send requests:
```powershell
$env:VITE_API_BASE_URL="https://bookkeeper-be-486079244466.asia-south1.run.app"
```

#### 2. Build the Frontend
This compiles your React code into the `dist` folder.
```powershell
cd src/frontend
npm install
npm run build
cd ../..
```

#### 3. Update Firebase Configuration (Verified)
We have already updated your `firebase.json` to point to `src/frontend/dist` and added the necessary rewrites. 

#### 4. Deploy to Firebase
Run the deployment command:
```powershell
firebase deploy --only hosting
```

### 💡 Why this works:
-   **`VITE_API_BASE_URL`**: By setting this before `npm run build`, Vite will "bake" your backend URL into the production code.
-   **`firebase deploy`**: This will now see the `dist` folder (containing all your React pages) and upload them to `books.helpsu.ai`.
-   **SPA Rewrites**: Since we added the `**` to `index.html` rewrite, your dashboard and other routes will work perfectly when you refresh the browser.

After these steps, your site should be fully live and connected to your Cloud Run backend!

