# Firebase Migration Guide

This guide explains how to migrate from Cloud SQL (PostgreSQL) to Firebase Firestore and how to switch the application to use Firebase.

## 1. Prerequisites
- Firebase project created.
- `firebase-admin` installed (`pip install -r requirements.txt`).
- **Application Default Credentials (ADC)** configured or `GOOGLE_APPLICATION_CREDENTIALS` environment variable set.
  - For local dev: `gcloud auth application-default login`
  - For Cloud Run: Ensure the service account has `Cloud Datastore User` (which covers Firestore) permissions.

## 2. Configuration Flag
The application uses the `DB_BACKEND` environment variable to determine which database to use.

- **`DB_BACKEND=SQL`** (Default): Uses PostgreSQL (Cloud SQL) or local SQLite.
- **`DB_BACKEND=FIREBASE`**: Uses Firebase Firestore.

## 3. Data Migration
We provide a script `migrate_to_firebase.py` to port your data from SQL to Firestore.

### Steps:
1. Ensure your `.env` file contains your current Cloud SQL or SQLite connection details.
2. Ensure you have access to your Firebase project via ADC.
3. Run the migration script:
   ```bash
   python migrate_to_firebase.py
   ```
4. The script will read all Users, Businesses, Transactions, and Processed Messages and write them to Firestore collections.

## 4. Switching in Production
1. Go to your Cloud Run service configuration.
2. Add/Update the environment variable:
   - `DB_BACKEND=FIREBASE`
3. Deploy the new configuration.
4. Once verified, you can safely shutdown and remove the Cloud SQL instance.

## 5. Technical Implementation
- **`src/firestore_service.py`**: Implements a lightweight SQLAlchemy-compatible interface for Firestore.
- **`src/db_service.py`**: Swaps between SQLAlchemy and Firestore based on the `DB_BACKEND` flag.

## 6. Verifying the Switch
You can verify which database is being used by checking your Cloud Run logs. You should see:
- `INFO:src.db_service:Using FIREBASE as database backend`
- `INFO:src.firestore_service:Firebase initialized with...`

### Supported SQLAlchemy-like operations in Firestore:
- `db.query(Model).filter(Model.field == value).first()`
- `db.query(Model).filter(Model.field == value).all()`
- `db.add(obj)`
- `db.commit()`
- `db.refresh(obj)`
- `db.delete(obj)`
