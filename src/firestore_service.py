import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize Firebase
if not firebase_admin._apps:
    try:
        # 1. Check for environment variable path (Production/Secret Manager)
        env_path = os.getenv("FIREBASE_CONFIG_PATH")
        # 2. Check for local file in root
        root_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase_key.json")
        
        final_path = env_path if env_path and os.path.exists(env_path) else (root_path if os.path.exists(root_path) else None)

        if final_path:
            cred = credentials.Certificate(final_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized with certificate: {final_path}")
        else:
            # 3. Fallback to ADC (Service Account on Cloud Run)
            firebase_admin.initialize_app()
            logger.info("Firebase initialized with Application Default Credentials (ADC)")
    except Exception as e:
        logger.warning(f"Could not initialize Firebase with ADC: {e}")
        # Fallback for local testing if needed, though ADC should work on GCP
        try:
            firebase_admin.initialize_app()
        except:
            pass

db_client = firestore.client()

class Field:
    def __init__(self, name):
        self.name = name
    def __eq__(self, other):
        return (self.name, "==", other)
    def __gt__(self, other):
        return (self.name, ">", other)
    def __lt__(self, other):
        return (self.name, "<", other)
    def __ge__(self, other):
        return (self.name, ">=", other)
    def __le__(self, other):
        return (self.name, "<=", other)
    def in_(self, values):
        return (self.name, "in", values)
    def desc(self):
        return (self.name, "DESCENDING")

class FirestoreModel:
    _collection = None
    _pk = None
    
    def __init__(self, **kwargs):
        # Initialize all defined Fields as None to avoid AttributeErrors
        for name, attr in self.__class__.__dict__.items():
            if isinstance(attr, Field):
                setattr(self, name, None)
        
        # Set provided values
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def to_dict(self):
        # Ensure the PK is included in the dictionary for in-memory logic
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        if self._pk and hasattr(self, self._pk) and self._pk not in data:
            data[self._pk] = getattr(self, self._pk)
        return data

class User(FirestoreModel):
    _collection = "users"
    _pk = "whatsapp_id"
    whatsapp_id = Field("whatsapp_id")
    google_email = Field("google_email")
    google_refresh_token = Field("google_refresh_token")
    active_business_id = Field("active_business_id")
    drive_initialized = Field("drive_initialized")
    subscription_status = Field("subscription_status")
    last_interaction_type = Field("last_interaction_type")
    last_interaction_data = Field("last_interaction_data")
    link_token = Field("link_token")
    link_token_expires_at = Field("link_token_expires_at")
    created_at = Field("created_at")

class Business(FirestoreModel):
    _collection = "businesses"
    _pk = "id"
    id = Field("id")
    user_whatsapp_id = Field("user_whatsapp_id")
    business_name = Field("business_name")
    business_gstin = Field("business_gstin")
    drive_folder_id = Field("drive_folder_id")
    master_ledger_sheet_id = Field("master_ledger_sheet_id")
    invoice_template_id = Field("invoice_template_id")
    is_active = Field("is_active")
    created_at = Field("created_at")

class Transaction(FirestoreModel):
    _collection = "transactions"
    _pk = "id"
    id = Field("id")
    user_whatsapp_id = Field("user_whatsapp_id")
    business_id = Field("business_id")
    transaction_type = Field("transaction_type")
    media_url = Field("media_url")
    extracted_json = Field("extracted_json")
    status = Field("status")
    extraction_provider = Field("extraction_provider")
    provider_model = Field("provider_model")
    confidence_score = Field("confidence_score")
    field_confidence = Field("field_confidence")
    needs_review = Field("needs_review")
    review_reason = Field("review_reason")
    created_at = Field("created_at")

class ProcessedMessage(FirestoreModel):
    _collection = "processed_messages"
    _pk = "message_id"
    message_id = Field("message_id")
    created_at = Field("created_at")

class GSTCache(FirestoreModel):
    _collection = "gst_cache"
    _pk = "query_key"
    query_key = Field("query_key")  # e.g., "hsn_123456" or "desc_keyboard"
    result_data = Field("result_data")
    provider = Field("provider")
    updated_at = Field("updated_at")

class FirestoreQuery:
    def __init__(self, model_class, session):
        self.model_class = model_class
        self.session = session
        self.collection_ref = db_client.collection(model_class._collection)
        self.query_ref = self.collection_ref
        self._in_memory_filters = []
        self._order_by_args = []

    def filter(self, *conditions):
        for condition in conditions:
            if isinstance(condition, tuple) and len(condition) == 3:
                field, op, value = condition
                # Use in-memory filtering for 'in' operator to avoid index requirements
                if op == "in":
                    self._in_memory_filters.append(condition)
                else:
                    # Use native Firestore where for simple equality
                    self.query_ref = self.query_ref.where(field_path=field, op_string=op, value=value)
        return self

    def limit(self, count):
        self.query_ref = self.query_ref.limit(count)
        return self

    def order_by(self, *args):
        # Store order_by to apply later
        self._order_by_args.extend(args)
        return self

    def _apply_in_memory_logic(self, docs):
        results = []
        for doc in docs:
            data = doc.to_dict()
            match = True
            for field, op, value in self._in_memory_filters:
                if op == "in":
                    if data.get(field) not in value:
                        match = False
                        break
            if match:
                results.append(doc)
        
        # Apply Sorting in-memory if multiple fields or complex query
        if self._order_by_args:
            for arg in reversed(self._order_by_args):
                if isinstance(arg, tuple) and len(arg) == 2:
                    field, direction = arg
                    reverse = (direction == "DESCENDING")
                else:
                    field = arg
                    reverse = False
                
                results.sort(key=lambda d: d.to_dict().get(field, ""), reverse=reverse)
                
        return results

    def first(self):
        try:
            # Try native first
            native_query = self.query_ref
            for arg in self._order_by_args:
                if isinstance(arg, tuple) and len(arg) == 2:
                    field, direction = arg
                    if direction == "DESCENDING":
                        native_query = native_query.order_by(field, direction=firestore.Query.DESCENDING)
                    else:
                        native_query = native_query.order_by(field)
                else:
                    native_query = native_query.order_by(arg)

            docs = native_query.limit(100).get() # Fetch a larger batch to filter in-memory
            processed = self._apply_in_memory_logic(docs)
            if processed:
                data = processed[0].to_dict()
                obj = self.model_class(**data)
                return self.session._track(obj)
        except Exception as e:
            if "index" in str(e).lower():
                logger.warning(f"Firestore Index missing, falling back to in-memory filtering: {e}")
                # Fallback: Fetch more docs and filter entirely in-memory
                # Note: We use query_ref which only has the simple filters applied
                docs = self.query_ref.limit(200).get()
                logger.info(f"Fallback: Fetched {len(docs)} docs for in-memory filtering")
                processed = self._apply_in_memory_logic(docs)
                if processed:
                    logger.info("Fallback: Found matching doc in-memory")
                    data = processed[0].to_dict()
                    obj = self.model_class(**data)
                    return self.session._track(obj)
                else:
                    logger.info("Fallback: No matching docs found in-memory")
            else:
                logger.error(f"Error in Firestore first(): {e}")
                raise
        return None

    def all(self):
        try:
            native_query = self.query_ref
            for arg in self._order_by_args:
                if isinstance(arg, tuple) and len(arg) == 2:
                    field, direction = arg
                    if direction == "DESCENDING":
                        native_query = native_query.order_by(field, direction=firestore.Query.DESCENDING)
                    else:
                        native_query = native_query.order_by(field)
                else:
                    native_query = native_query.order_by(arg)
            
            docs = native_query.get()
            processed = self._apply_in_memory_logic(docs)
            return [self.session._track(self.model_class(**doc.to_dict())) for doc in processed]
        except Exception as e:
            if "index" in str(e).lower():
                logger.warning(f"Firestore Index missing, falling back to in-memory filtering (all): {e}")
                docs = self.query_ref.get()
                processed = self._apply_in_memory_logic(docs)
                return [self.session._track(self.model_class(**doc.to_dict())) for doc in processed]
            raise

    def count(self):
        return len(self.all())

    def delete(self):
        """Bulk delete for queries"""
        docs = self.query_ref.get()
        for doc in docs:
            doc.reference.delete()
        return True

    def update(self, values):
        docs = self.query_ref.get()
        for doc in docs:
            doc.reference.update(values)

class FirestoreSession:
    def __init__(self):
        self.to_add = []
        self.to_delete = []
        self.identity_map = {} # Track objects to detect changes

    def _track(self, obj):
        if obj:
            pk_val = getattr(obj, obj._pk)
            # Store a snapshot of the data to detect changes
            self.identity_map[f"{obj._collection}/{pk_val}"] = (obj, obj.to_dict())
        return obj

    def query(self, model_class):
        return FirestoreQuery(model_class, self)

    def add(self, obj):
        self.to_add.append(obj)
        self._track(obj)

    def delete(self, obj):
        self.to_delete.append(obj)

    def commit(self):
        try:
            # 1. Sync dirty objects (existing objects that were modified)
            for key, (obj, original_dict) in self.identity_map.items():
                current_dict = obj.to_dict()
                if current_dict != original_dict:
                    pk_val = getattr(obj, obj._pk)
                    db_client.collection(obj._collection).document(str(pk_val)).set(current_dict)
                    logger.info(f"Firestore: Updated existing {obj._collection}/{pk_val}")

            # 2. Add new objects
            for obj in self.to_add:
                pk_val = getattr(obj, obj._pk)
                if not pk_val:
                    continue
                db_client.collection(obj._collection).document(str(pk_val)).set(obj.to_dict())
                logger.info(f"Firestore: Created new {obj._collection}/{pk_val}")
            
            # 3. Delete objects
            for obj in self.to_delete:
                pk_val = getattr(obj, obj._pk)
                db_client.collection(obj._collection).document(str(pk_val)).delete()
                logger.info(f"Firestore: Deleted {obj._collection}/{pk_val}")
                
        except Exception as e:
            logger.error(f"Firestore Commit Error: {str(e)}", exc_info=True)
            raise
        finally:
            self.to_add = []
            self.to_delete = []
            # Update identity map with fresh snapshots
            new_map = {}
            for key, (obj, _) in self.identity_map.items():
                 new_map[key] = (obj, obj.to_dict())
            self.identity_map = new_map

    def rollback(self):
        """No-op for Firestore mock layer as it doesn't support transactions yet"""
        self.to_add = []
        self.to_delete = []
        logger.info("Firestore: Rollback (cleared pending additions/deletions)")

    def refresh(self, obj):
        pk_val = getattr(obj, obj._pk)
        doc = db_client.collection(obj._collection).document(str(pk_val)).get()
        if doc.exists:
            for k, v in doc.to_dict().items():
                setattr(obj, k, v)
            self._track(obj)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass
