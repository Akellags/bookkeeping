import os
import logging
import time
import random
import requests
import httplib2
import google_auth_httplib2
import socket
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Set a very long global socket timeout for extremely slow networks (WinError 10060)
socket.setdefaulttimeout(300)

load_dotenv()

logger = logging.getLogger(__name__)

def is_transient_google_error(exception):
    """Returns True if the error is a transient Google API error (429, 5xx) or network issue"""
    if isinstance(exception, HttpError):
        # Retry on 429 (Rate Limit) or 5xx (Server Errors)
        return exception.resp.status in [429, 500, 502, 503, 504]
    
    # Check for connection errors
    exc_str = str(exception).lower()
    if "connection" in exc_str or "timeout" in exc_str or "10060" in exc_str:
        return True
        
    return False

# Reusable tenacity decorator for Google API calls
google_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception(is_transient_google_error)
)

class GoogleService:
    def __init__(self, refresh_token: str):
        # Initialize Google API clients with user's refresh token
        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        
        # We keep the build() services for discovery-based logic (uploading files)
        # but we'll use a custom requests executor for standard data operations
        http = httplib2.Http(timeout=150) 
        authorized_http = google_auth_httplib2.AuthorizedHttp(self.creds, http=http)

        self.drive_service = build("drive", "v3", http=authorized_http, cache_discovery=False)
        self.sheets_service = build("sheets", "v4", http=authorized_http, cache_discovery=False)
        self.docs_service = build("docs", "v1", http=authorized_http, cache_discovery=False)
        
        self._sheet_cache = {}

    def _execute_with_requests(self, method, url, body=None, params=None):
        """Executes a Google API call using requests with a long timeout to bypass httplib2 10060 errors"""
        if not self.creds.valid:
            self.creds.refresh(Request())
            
        headers = {
            "Authorization": f"Bearer {self.creds.token}",
            "Content-Type": "application/json"
        }
        
        # Retry logic for 10060/timeouts at the request level
        for attempt in range(3):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    params=params,
                    timeout=150 # Very long timeout for slow connections
                )
                response.raise_for_status()
                return response.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt == 2: raise
                logger.warning(f"Request timeout/error (attempt {attempt+1}): {e}. Retrying...")
                time.sleep(2)
        return None

    def _get_ledger_headers(self):
        """Returns the standard GSTR-1 compliant headers for the Master Ledger"""
        return [
            "Recipient GSTIN", "Receiver Name", "Invoice Number", "Invoice date", 
            "Invoice Value", "Place Of Supply", "Reverse Charge", "Invoice Type",
            "Transaction Type", "HSN Code", "HSN Description", "UQC", "Quantity", 
            "Rate", "Taxable Value", "CGST", "SGST", "IGST", "Cess Amount",
            "Payment Status", "Due Date"
        ]

    def _get_payment_headers(self):
        """Returns headers for the Payments worksheet"""
        return [
            "Entity Name", "Amount", "Type (One-time/Recurring)", "Frequency (Monthly/Yearly)",
            "Last Payment Date", "Next Due Date", "Status", "Notes"
        ]

    def _resolve_sheet_name(self, spreadsheet_id: str, target_name: str):
        """Resolves target_name to the actual sheet name in the spreadsheet (e.g. Sales vs Sale)"""
        cache_key = f"{spreadsheet_id}_{target_name}"
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key]

        # DO NOT use @google_retry here to avoid infinite loops on connection issues
        try:
            # Use requests direct to avoid httplib2 10060
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            spreadsheet = self._execute_with_requests("GET", url)
            
            if not spreadsheet: return target_name
            
            sheets = [s.get("properties", {}).get("title") for s in spreadsheet.get("sheets", [])]
            
            logger.info(f"DEBUG: Found {len(sheets)} sheets in spreadsheet {spreadsheet_id}: {sheets}")
            
            # Cache ALL sheets for this spreadsheet to minimize future network calls
            for s in sheets:
                # Cache exact, plural, and singular variations
                s_norm = s.strip().lower()
                self._sheet_cache[f"{spreadsheet_id}_{s}"] = s
                
                # If it's a known type, cache it for the target
                for t in ["Sales", "Purchases", "Expenses", "Payments"]:
                    t_norm = t.lower()
                    if s_norm == t_norm or s_norm == t_norm[:-1] or s_norm == t_norm + "s":
                         logger.info(f"DEBUG: Mapping target '{t}' to existing sheet '{s}'")
                         self._sheet_cache[f"{spreadsheet_id}_{t}"] = s

            # Re-check cache after mass-population
            if cache_key in self._sheet_cache:
                return self._sheet_cache[cache_key]

            # Manual check if not already returned
            target_norm = target_name.strip().lower()
            for s in sheets:
                s_norm = s.strip().lower()
                if s_norm == target_norm or s_norm == target_norm[:-1] or s_norm == target_norm + "s":
                    self._sheet_cache[cache_key] = s
                    return s

            if target_name in ["Sales", "Purchases", "Expenses"] and "Sheet1" in sheets:
                self._sheet_cache[cache_key] = "Sheet1"
                return "Sheet1"

        except Exception as e:
            logger.warning(f"Could not resolve sheet name via API: {e}. Using fallback: {target_name}")
            # Do not re-raise or retry, just fallback to avoid blocking the main transaction
        
        return target_name

    @google_retry
    def initialize_user_drive(self):
        """Idempotently sets up 'Help U' folder, 'Master_Ledger', and 'Invoice_Template' in user's Drive"""
        # 1. Check for existing Help U Folder
        q = "name = 'Help U' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.drive_service.files().list(q=q, fields="files(id)").execute()
        files = results.get("files", [])
        
        if files:
            folder_id = files[0]["id"]
            logger.info(f"Found existing 'Help U' folder: {folder_id}")
        else:
            folder_metadata = {
                "name": "Help U",
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = self.drive_service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder.get("id")
            logger.info(f"Created new 'Help U' folder: {folder_id}")

        # 2. Check for existing Master Ledger Sheet inside the folder
        q = f"name = 'Master_Ledger' and parents in '{folder_id}' and trashed = false"
        results = self.drive_service.files().list(q=q, fields="files(id)").execute()
        files = results.get("files", [])
        
        if files:
            sheet_id = files[0]["id"]
            logger.info(f"Found existing 'Master_Ledger': {sheet_id}")
            
            # Ensure all required worksheets exist: Sales, Purchases, Expenses, Payments
            # Use requests for metadata to avoid 10060
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            spreadsheet = self._execute_with_requests("GET", url)
            
            if not spreadsheet:
                logger.error(f"Failed to fetch spreadsheet {sheet_id} during initialization")
                return folder_id, None, None

            sheet_objs = spreadsheet.get("sheets", [])
            existing_sheets = [s.get("properties", {}).get("title") for s in sheet_objs]
            
            # 1. Migration: If 'Sheet1' exists and 'Sales' doesn't, rename it.
            if "Sheet1" in existing_sheets and "Sales" not in existing_sheets:
                sheet1_id = next(s.get("properties", {}).get("sheetId") for s in sheet_objs if s.get("properties", {}).get("title") == "Sheet1")
                batch_update_request = {
                    "requests": [{"updateSheetProperties": {"properties": {"sheetId": sheet1_id, "title": "Sales"}, "fields": "title"}}]
                }
                # Use requests for batchUpdate
                update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
                self._execute_with_requests("POST", update_url, body=batch_update_request)
                logger.info(f"Migrated 'Sheet1' to 'Sales' for existing ledger: {sheet_id}")
                # Refresh existing_sheets list after rename
                existing_sheets = ["Sales" if s == "Sheet1" else s for s in existing_sheets]
            
            # 2. Add any other missing sheets
            required_sheets = ["Sales", "Purchases", "Expenses", "Payments"]
            update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
            for s_name in required_sheets:
                if s_name not in existing_sheets:
                    batch_update_request = {
                        "requests": [{"addSheet": {"properties": {"title": s_name}}}]
                    }
                    self._execute_with_requests("POST", update_url, body=batch_update_request)
                    headers = self._get_payment_headers() if s_name == "Payments" else self._get_ledger_headers()
                    self.append_to_master_ledger(sheet_id, headers, sheet_name=s_name)
                    logger.info(f"Added missing sheet '{s_name}' to Master_Ledger")
            
            # 3. Header Repair: Ensure headers are up to date in existing sheets (Sales/Purchases/Expenses)
            for s_name in ["Sales", "Purchases", "Expenses"]:
                resolved_s_name = self._resolve_sheet_name(sheet_id, s_name)
                # Use requests for values.get
                val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_s_name}'!A1:U1"
                val_result = self._execute_with_requests("GET", val_url)
                current_headers = val_result.get("values", [[]])[0] if val_result else []
                
                target_headers = self._get_ledger_headers()
                if len(current_headers) < len(target_headers):
                    # Update row 1 with correct headers via requests
                    update_val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_s_name}'!A1:U1"
                    params = {"valueInputOption": "USER_ENTERED"}
                    body = {"values": [target_headers]}
                    self._execute_with_requests("PUT", update_val_url, body=body, params=params)
                    logger.info(f"Repaired/Updated headers for sheet '{resolved_s_name}' in {sheet_id}")
        else:
            sheet_metadata = {
                "name": "Master_Ledger",
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "parents": [folder_id]
            }
            sheet = self.drive_service.files().create(body=sheet_metadata, fields="id").execute()
            sheet_id = sheet.get("id")
            
            # Initialize with required worksheets
            # First sheet is usually 'Sheet1', rename it to 'Sales'
            spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            first_sheet_id = spreadsheet.get("sheets", [])[0].get("properties", {}).get("sheetId")
            
            batch_update_request = {
                "requests": [
                    {"updateSheetProperties": {"properties": {"sheetId": first_sheet_id, "title": "Sales"}, "fields": "title"}},
                    {"addSheet": {"properties": {"title": "Purchases"}}},
                    {"addSheet": {"properties": {"title": "Expenses"}}},
                    {"addSheet": {"properties": {"title": "Payments"}}}
                ]
            }
            self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=batch_update_request).execute()
            
            # Initialize Sheet Headers for all
            headers = self._get_ledger_headers()
            pay_headers = self._get_payment_headers()
            for s_name in ["Sales", "Purchases", "Expenses"]:
                self.append_to_master_ledger(sheet_id, headers, sheet_name=s_name)
            self.append_to_master_ledger(sheet_id, pay_headers, sheet_name="Payments")
            
            logger.info(f"Created new 'Master_Ledger' with Sales, Purchases, Expenses, Payments sheets: {sheet_id}")

        # 3. Check for existing Invoice Template Doc
        q = f"name = 'Invoice_Template' and parents in '{folder_id}' and trashed = false"
        results = self.drive_service.files().list(q=q, fields="files(id)").execute()
        files = results.get("files", [])
        
        if files:
            doc_id = files[0]["id"]
            logger.info(f"Found existing 'Invoice_Template': {doc_id}")
        else:
            master_template_id = os.getenv("GOOGLE_INVOICE_TEMPLATE_ID")
            if master_template_id:
                doc_metadata = {"name": "Invoice_Template", "parents": [folder_id]}
                doc = self.drive_service.files().copy(fileId=master_template_id, body=doc_metadata, fields="id").execute()
                doc_id = doc.get("id")
            else:
                doc_metadata = {
                    "name": "Invoice_Template",
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [folder_id]
                }
                doc = self.drive_service.files().create(body=doc_metadata, fields="id").execute()
                doc_id = doc.get("id")
                # Initialize basic content
                template_text = (
                    "{{ business_name }}\nGSTIN: {{ business_gstin }}\n\nTAX INVOICE\n\n"
                    "Invoice No: {{ invoice_no }}\nDate: {{ date }}\n\n"
                    "Bill To:\n{{ customer_name }}\nGSTIN: {{ recipient_gstin }}\n\n"
                    "Description: Goods/Services\nHSN: {{ hsn_code }}\nRate: {{ gst_rate }}%\n"
                    "Taxable Value: Rs. {{ taxable_value }}\n\n"
                    "CGST: Rs. {{ cgst }}\nSGST: Rs. {{ sgst }}\nIGST: Rs. {{ igst }}\n\n"
                    "Total Amount: Rs. {{ total_amount }}\n"
                )
                try:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id, 
                        body={"requests": [{"insertText": {"location": {"index": 1}, "text": template_text}}]}
                    ).execute()
                except Exception as e:
                    logger.warning(f"Failed to initialize template: {e}")

        return folder_id, sheet_id, doc_id

    @google_retry
    def upload_bill_image(self, file_path: str, folder_id: str):
        """Uploads bill image to user's Drive in specific folder"""
        file_metadata = {
            "name": os.path.basename(file_path),
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype="image/jpeg")
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        return file.get("id")

    @google_retry
    def append_to_master_ledger(self, sheet_id: str, row_data: list, sheet_name: str = "Sales"):
        """Appends a new transaction row to the Master Ledger Google Sheet using requests for stability"""
        start_time = time.time()
        resolved_name = self._resolve_sheet_name(sheet_id, sheet_name)
        resolve_done = time.time()
        
        range_name = f"'{resolved_name}'!A:U"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}:append"
        params = {"valueInputOption": "USER_ENTERED"}
        body = {"values": [row_data]}
        
        result = self._execute_with_requests("POST", url, body=body, params=params)
        end_time = time.time()
        
        duration = end_time - start_time
        resolve_duration = resolve_done - start_time
        append_duration = end_time - resolve_done
        
        print(f"  [TIMER] Google Sheet Append ({sheet_name}): Total {duration:.2f}s (Resolve: {resolve_duration:.2f}s, Append: {append_duration:.2f}s)")
        
        return result

    @google_retry
    def update_ledger_row(self, sheet_id: str, row_index: int, row_data: list, sheet_name: str = "Sales"):
        """Updates a specific row in the Master Ledger (row_index is 1-based) using requests for stability"""
        resolved_name = self._resolve_sheet_name(sheet_id, sheet_name)
        range_name = f"'{resolved_name}'!A{row_index}:U{row_index}"
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"
        params = {"valueInputOption": "USER_ENTERED"}
        body = {"values": [row_data]}
        
        return self._execute_with_requests("PUT", url, body=body, params=params)

    @google_retry
    def get_last_ledger_row(self, sheet_id: str, sheet_name: str = "Sales"):
        """Returns the last data row and its 1-based index from the Master Ledger using requests for stability"""
        resolved_name = self._resolve_sheet_name(sheet_id, sheet_name)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_name}'!A:U"
        
        result = self._execute_with_requests("GET", url)
        if not result:
            return None, None
            
        values = result.get("values", [])
        if not values or len(values) <= 1:
            return None, None
        return values[-1], len(values)

    def generate_gstr1_json(self, sheet_id: str, gstin: str, fp: str):
        """Generates GSTR-1 compatible JSON from the Master Ledger (B2B, B2CS, HSN, DOC)"""
        # Ensure input GSTIN is uppercase
        gstin = str(gstin).strip().upper()
        
        rows = self.get_ledger_rows(sheet_id, sheet_name="Sales")
        if not rows or len(rows) <= 1:
            return None

        # fp format is MMYYYY
        target_month = fp[:2]
        target_year = fp[2:]

        data_rows = rows[1:]
        b2b_invoices = []
        b2cs_invoices = []
        hsn_data = []
        
        # Doc Summary trackers
        min_inv = None
        max_inv = None
        total_docs = 0
        
        for row in data_rows:
            # Basic validation
            if len(row) < 15:
                continue
                
            # Filter by tax period (fp) from Invoice Date (Col 3: DD-MM-YYYY)
            inv_date = str(row[3])
            if not inv_date or "-" not in inv_date:
                continue
                
            date_parts = inv_date.split("-")
            if len(date_parts) != 3:
                continue
                
            inv_month = date_parts[1]
            inv_year = date_parts[2]
            
            if inv_month != target_month or inv_year != target_year:
                continue

            total_docs += 1
            inv_no = str(row[2]).strip().upper()
            if not min_inv or inv_no < min_inv: min_inv = inv_no
            if not max_inv or inv_no > max_inv: max_inv = inv_no

            inv_type = row[7]
            # Ensure POS is zero-padded 2 digits
            pos = str(row[5]).strip()
            if pos.isdigit() and len(pos) == 1:
                pos = f"0{pos}"
            elif not pos:
                pos = "37" # Default

            if inv_type == "B2B":
                recipient_gstin = str(row[0]).strip().upper()
                
                # Item detail for this row
                item_detail = {
                    "num": 1,
                    "itm_det": {
                        "rt": float(row[13] or 0),
                        "txval": round(float(row[14] or 0), 2),
                        "camt": round(float(row[15] or 0), 2),
                        "samt": round(float(row[16] or 0), 2),
                        "iamt": round(float(row[17] or 0), 2),
                        "csamt": round(float(row[18] or 0), 2)
                    }
                }

                # Find or create vendor
                vendor = next((v for v in b2b_invoices if v["ctin"] == recipient_gstin), None)
                if not vendor:
                    vendor = {"ctin": recipient_gstin, "inv": []}
                    b2b_invoices.append(vendor)
                
                # Find or create invoice
                invoice = next((i for i in vendor["inv"] if i["inum"] == inv_no), None)
                if invoice:
                    # Update item number and append
                    item_detail["num"] = len(invoice["itms"]) + 1
                    invoice["itms"].append(item_detail)
                else:
                    invoice = {
                        "inum": inv_no,
                        "idt": row[3],
                        "val": round(float(row[4] or 0), 2),
                        "pos": pos,
                        "rchrg": row[6] or "N",
                        "itms": [item_detail]
                    }
                    vendor["inv"].append(invoice)
            else:
                # B2CS Summary
                rt = float(row[13] or 0)
                sply_ty = "INTER" if float(row[17] or 0) > 0 else "INTRA"
                
                found_b2cs = False
                for b in b2cs_invoices:
                    if b["pos"] == pos and b["rt"] == rt:
                        b["txval"] = round(b["txval"] + float(row[14] or 0), 2)
                        b["iamt"] = round(b["iamt"] + float(row[17] or 0), 2)
                        b["camt"] = round(b["camt"] + float(row[15] or 0), 2)
                        b["samt"] = round(b["samt"] + float(row[16] or 0), 2)
                        b["csamt"] = round(b["csamt"] + float(row[18] or 0), 2)
                        found_b2cs = True
                        break
                
                if not found_b2cs:
                    b2cs_invoices.append({
                        "sply_ty": sply_ty,
                        "pos": pos,
                        "typ": "OE",
                        "rt": rt,
                        "txval": round(float(row[14] or 0), 2),
                        "iamt": round(float(row[17] or 0), 2),
                        "camt": round(float(row[15] or 0), 2),
                        "samt": round(float(row[16] or 0), 2),
                        "csamt": round(float(row[18] or 0), 2)
                    })

            # HSN Summary (Table 12)
            hsn_code = str(row[9]).strip() or "OTH"
            uqc_code = str(row[11]).strip().upper() or "OTH"
            found_hsn = False
            for h in hsn_data:
                if h["hsn_sc"] == hsn_code and h["uqc"] == uqc_code:
                    h["qty"] = round(h["qty"] + float(row[12] or 1), 2)
                    h["val"] = round(h["val"] + float(row[4] or 0), 2)
                    h["txval"] = round(h["txval"] + float(row[14] or 0), 2)
                    h["iamt"] = round(h["iamt"] + float(row[17] or 0), 2)
                    h["camt"] = round(h["camt"] + float(row[15] or 0), 2)
                    h["samt"] = round(h["samt"] + float(row[16] or 0), 2)
                    h["csamt"] = round(h["csamt"] + float(row[18] or 0), 2)
                    found_hsn = True
                    break
            if not found_hsn:
                hsn_data.append({
                    "num": len(hsn_data) + 1,
                    "hsn_sc": hsn_code,
                    "desc": str(row[10] or "Goods/Services")[:30],
                    "uqc": uqc_code,
                    "qty": round(float(row[12] or 1), 2),
                    "val": round(float(row[4] or 0), 2),
                    "txval": round(float(row[14] or 0), 2),
                    "iamt": round(float(row[17] or 0), 2),
                    "camt": round(float(row[15] or 0), 2),
                    "samt": round(float(row[16] or 0), 2),
                    "csamt": round(float(row[18] or 0), 2)
                })

        # Doc Summary (Table 13)
        doc_issue = {
            "doc_det": [{
                "doc_num": 1,
                "docs": [{
                    "from": min_inv or "N/A",
                    "to": max_inv or "N/A",
                    "totcnt": total_docs,
                    "cancel": 0,
                    "net_issue": total_docs
                }]
            }]
        }

        return {
            "gstin": gstin,
            "fp": fp,
            "gt": 0.00,
            "cur_gt": 0.00,
            "b2b": b2b_invoices,
            "b2cs": b2cs_invoices,
            "hsn": {"data": hsn_data},
            "doc_issue": doc_issue
        }

    def generate_invoice_pdf_buffer(self, sheet_id: str, invoice_no: str, user_profile: dict = None):
        """Generates a PDF for a specific invoice number from sheet data and returns it as a BytesIO buffer"""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        from io import BytesIO

        rows = self.get_ledger_rows(sheet_id)
        if not rows or len(rows) <= 1:
            return None
            
        invoice_row = None
        for row in rows[1:]:
            if len(row) > 2 and row[2] == invoice_no: # Column C: Invoice Number
                invoice_row = row
                break
        
        if not invoice_row:
            return None

        # Headers mapping for 19-column structure:
        # 0: Recipient GSTIN, 1: Receiver Name, 2: Invoice Number, 3: Invoice date, 
        # 4: Invoice Value, 5: Place Of Supply, 6: Reverse Charge, 7: Invoice Type,
        # 8: Transaction Type, 9: HSN Code, 10: HSN Description, 11: UQC, 12: Quantity, 
        # 13: Rate, 14: Taxable Value, 15: CGST, 16: SGST, 17: IGST, 18: Cess Amount

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2*cm, height-2*cm, user_profile.get("business_name", "Help U Traders"))
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, height-2.6*cm, f"GSTIN: {user_profile.get('business_gstin', '37ABCDE1234F1Z5')}")
        
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width/2, height-4*cm, "TAX INVOICE")
        
        # Invoice Details
        p.setFont("Helvetica", 11)
        p.drawString(2*cm, height-5*cm, f"Invoice No: {invoice_row[2]}")
        p.drawString(2*cm, height-5.6*cm, f"Date: {invoice_row[3]}")
        
        p.drawString(12*cm, height-5*cm, f"Bill To: {invoice_row[1]}")
        if len(invoice_row) > 0 and invoice_row[0]:
            p.drawString(12*cm, height-5.6*cm, f"GSTIN: {invoice_row[0]}")

        # Table Header
        p.line(2*cm, height-7*cm, width-2*cm, height-7*cm)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2.2*cm, height-7.5*cm, "Description")
        p.drawString(8*cm, height-7.5*cm, "HSN")
        p.drawString(10*cm, height-7.5*cm, "Rate")
        p.drawString(12*cm, height-7.5*cm, "Taxable Value")
        p.drawString(16*cm, height-7.5*cm, "Total")
        p.line(2*cm, height-8*cm, width-2*cm, height-8*cm)

        # Table Content
        p.setFont("Helvetica", 10)
        p.drawString(2.2*cm, height-8.6*cm, invoice_row[10] if len(invoice_row) > 10 else "Goods/Services")
        p.drawString(8*cm, height-8.6*cm, invoice_row[9] if len(invoice_row) > 9 else "")
        p.drawString(10*cm, height-8.6*cm, f"{invoice_row[13]}%" if len(invoice_row) > 13 else "0%")
        p.drawString(12*cm, height-8.6*cm, f"Rs. {invoice_row[14]}" if len(invoice_row) > 14 else "Rs. 0")
        p.drawString(16*cm, height-8.6*cm, f"Rs. {invoice_row[4]}" if len(invoice_row) > 4 else "Rs. 0")

        # Summary
        p.line(10*cm, height-10*cm, width-2*cm, height-10*cm)
        p.drawString(11*cm, height-10.6*cm, f"Taxable Value:")
        p.drawRightString(width-2.5*cm, height-10.6*cm, f"{invoice_row[14]}" if len(invoice_row) > 14 else "0")
        
        p.drawString(11*cm, height-11.2*cm, f"CGST:")
        p.drawRightString(width-2.5*cm, height-11.2*cm, f"{invoice_row[15]}" if len(invoice_row) > 15 else "0")
        p.drawString(11*cm, height-11.8*cm, f"SGST:")
        p.drawRightString(width-2.5*cm, height-11.8*cm, f"{invoice_row[16]}" if len(invoice_row) > 16 else "0")
        p.drawString(11*cm, height-12.4*cm, f"IGST:")
        p.drawRightString(width-2.5*cm, height-12.4*cm, f"{invoice_row[17]}" if len(invoice_row) > 17 else "0")
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(11*cm, height-13.4*cm, f"Total Amount:")
        p.drawRightString(width-2.5*cm, height-13.4*cm, f"Rs. {invoice_row[4]}" if len(invoice_row) > 4 else "Rs. 0")

        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width/2, 2*cm, "This is a computer generated invoice.")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @google_retry
    def get_ledger_rows(self, sheet_id: str, start_date: str = None, end_date: str = None, sheet_name: str = "Sales"):
        """Fetches all rows from the Master Ledger with optional date filtering using requests for stability"""
        try:
            from datetime import datetime
            resolved_name = self._resolve_sheet_name(sheet_id, sheet_name)
            range_name = f"'{resolved_name}'!A1:U"
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"
            result = self._execute_with_requests("GET", url)
            
            if not result:
                return []
                
            rows = result.get("values", [])
            if not rows:
                return []
            
            if not start_date and not end_date:
                return rows
                
            header = rows[0]
            data_rows = rows[1:]
            filtered_rows = [header]
            
            s_dt = datetime.strptime(start_date, "%d-%m-%Y") if start_date else None
            e_dt = datetime.strptime(end_date, "%d-%m-%Y") if end_date else None
            
            for row in data_rows:
                if len(row) >= 4:
                    try:
                        row_dt = datetime.strptime(row[3], "%d-%m-%Y")
                        if s_dt and row_dt < s_dt:
                            continue
                        if e_dt and row_dt > e_dt:
                            continue
                    except:
                        pass # Skip invalid dates
                filtered_rows.append(row)
            return filtered_rows
        except Exception as e:
            logger.error(f"Error fetching ledger rows: {e}")
            return []

    def get_ledger_stats(self, sheet_id: str, start_date: str = None, end_date: str = None):
        """Fetches and aggregates stats from Sales, Purchases, Expenses, and Payments sheets"""
        try:
            stats = {
                "count": 0,
                "total_sales": 0, "unpaid_sales": 0, "sales_count": 0,
                "total_purchases": 0, "unpaid_purchases": 0, "purchases_count": 0,
                "total_expenses": 0, "paid_expenses": 0, "unpaid_expenses": 0, "expenses_count": 0,
                "total_payments": 0, "payments_count": 0
            }
            
            # 1. Sales Stats
            sales_rows = self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Sales")
            if len(sales_rows) > 1:
                data = sales_rows[1:]
                stats["sales_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_sales"] += val
                    if len(row) > 19 and row[19] == "Unpaid":
                        stats["unpaid_sales"] += val
            
            # 2. Purchases Stats
            purchases_rows = self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Purchases")
            if len(purchases_rows) > 1:
                data = purchases_rows[1:]
                stats["purchases_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_purchases"] += val
                    if len(row) > 19 and row[19] == "Unpaid":
                        stats["unpaid_purchases"] += val
            
            # 3. Expenses Stats
            expenses_rows = self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Expenses")
            if len(expenses_rows) > 1:
                data = expenses_rows[1:]
                stats["expenses_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_expenses"] += val
                    # For Expenses, column 19 is status (Paid/Unpaid)
                    if len(row) > 19:
                        if row[19] == "Unpaid":
                            stats["unpaid_expenses"] += val
                        else:
                            stats["paid_expenses"] += val
                    else:
                        stats["paid_expenses"] += val

            # 4. Payments Stats
            payments_rows = self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Payments")
            if len(payments_rows) > 1:
                data = payments_rows[1:]
                stats["payments_count"] = len(data)
                for row in data:
                    # Payments structure: Entity Name, Amount, Type, Frequency, Last Date, Next Due, Status, Notes
                    # Amount is at index 1
                    val = float(row[1] or 0)
                    stats["total_payments"] += val

            stats["count"] = stats["sales_count"] + stats["purchases_count"] + stats["expenses_count"] + stats["payments_count"]
            return stats
        except Exception as e:
            logger.error(f"Error fetching ledger stats: {e}")
            return {
                "count": 0,
                "total_sales": 0, "unpaid_sales": 0, "sales_count": 0,
                "total_purchases": 0, "unpaid_purchases": 0, "purchases_count": 0,
                "total_expenses": 0, "paid_expenses": 0, "unpaid_expenses": 0, "expenses_count": 0,
                "total_payments": 0, "payments_count": 0
            }

    @google_retry
    def generate_sales_invoice(self, template_id: str, data: dict, output_folder_id: str):
        """Creates a Google Doc from template, replaces placeholders, and exports to PDF"""
        # 1. Copy template
        copy_metadata = {"name": f"Invoice_{data['invoice_no']}", "parents": [output_folder_id]}
        copy = self.drive_service.files().copy(fileId=template_id, body=copy_metadata).execute()
        doc_id = copy.get("id")

        # 2. Replace placeholders in Doc
        requests = []
        for key, value in data.items():
            requests.append({
                "replaceAllText": {
                    "containsText": {"text": f"{{{{ {key} }}}}"},
                    "replaceText": str(value)
                }
            })
        
        self.docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

        # 3. Export to PDF (return link or file content)
        # This will be refined to return a downloadable link or WhatsApp-ready file
        return doc_id

    def get_business_summary(self, sheet_id: str):
        """Aggregates ledger data into a summary for AI Consultant Agent"""
        from datetime import datetime, timedelta
        from collections import Counter
        
        rows = self.get_ledger_rows(sheet_id)
        if not rows or len(rows) <= 1:
            return None
            
        data_rows = rows[1:]
        today = datetime.now()
        this_month = today.strftime("%m-%Y")
        last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%m-%Y")
        
        summary = {
            "this_month": {"sales": 0, "purchases": 0, "gst_collected": 0, "gst_paid": 0},
            "last_month": {"sales": 0, "purchases": 0},
            "top_customers": Counter(),
            "top_vendors": Counter(),
            "overdue_payments": [],
            "total_unpaid": 0
        }
        
        for row in data_rows:
            if len(row) < 9: continue
            
            try:
                val = float(row[4] or 0)
                tx_type = row[8]
                dt_str = row[3]
                dt_obj = datetime.strptime(dt_str, "%d-%m-%Y")
                row_month = dt_obj.strftime("%m-%Y")
                
                gst_total = float(row[15] or 0) + float(row[16] or 0) + float(row[17] or 0)
                
                # 1. Monthly Aggregation
                if row_month == this_month:
                    if tx_type == "Sale":
                        summary["this_month"]["sales"] += val
                        summary["this_month"]["gst_collected"] += gst_total
                    else:
                        summary["this_month"]["purchases"] += val
                        summary["this_month"]["gst_paid"] += gst_total
                elif row_month == last_month:
                    if tx_type == "Sale":
                        summary["last_month"]["sales"] += val
                    else:
                        summary["last_month"]["purchases"] += val
                
                # 2. Entity Aggregation
                entity_name = row[1]
                if tx_type == "Sale":
                    summary["top_customers"][entity_name] += val
                else:
                    summary["top_vendors"][entity_name] += val
                    
                # 3. Overdue/Unpaid
                if len(row) > 19 and row[19] == "Unpaid":
                    summary["total_unpaid"] += val
                    due_date_str = row[20]
                    # Simple overdue check if date is parseable
                    try:
                        if due_date_str and due_date_str != "N/A":
                            # This needs a better parser but for now we look for common patterns
                            # or just list them as unpaid.
                            summary["overdue_payments"].append({
                                "entity": entity_name,
                                "amount": val,
                                "due": due_date_str,
                                "inv": row[2]
                            })
                    except: pass
                    
            except (ValueError, TypeError, IndexError):
                continue
                
        # Format Top Counters
        summary["top_customers"] = dict(summary["top_customers"].most_common(3))
        summary["top_vendors"] = dict(summary["top_vendors"].most_common(3))
        
        return summary
