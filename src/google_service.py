import os
import logging
import time
import random
import requests
import httplib2
import google_auth_httplib2
import socket
import asyncio
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
    _sheet_cache = {} # Class-level cache to persist across instances

    def __init__(self, refresh_token: str):
        # Initialize Google API clients with user's refresh token
        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=(os.getenv("GOOGLE_CLIENT_ID") or "").strip(),
            client_secret=(os.getenv("GOOGLE_CLIENT_SECRET") or "").strip(),
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        
        # We keep the build() services for discovery-based logic (uploading files)
        # but we'll use a custom requests executor for standard data operations
        http = httplib2.Http(timeout=150) 
        authorized_http = google_auth_httplib2.AuthorizedHttp(self.creds, http=http)

        self.drive_service = build("drive", "v3", http=authorized_http, cache_discovery=False)
        self.sheets_service = build("sheets", "v4", http=authorized_http, cache_discovery=False)
        self.docs_service = build("docs", "v1", http=authorized_http, cache_discovery=False)

    async def _execute_with_requests(self, method, url, body=None, params=None):
        """Executes a Google API call using requests with a long timeout to bypass httplib2 10060 errors"""
        if not self.creds.valid:
            # Credentials refresh is blocking, but fast enough for now
            self.creds.refresh(Request())
            
        headers = {
            "Authorization": f"Bearer {self.creds.token}",
            "Content-Type": "application/json"
        }
        
        # Retry logic for 10060/timeouts at the request level
        for attempt in range(3):
            try:
                # Use a thread pool for the blocking requests call
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=body,
                        params=params,
                        timeout=150
                    )
                )
                response.raise_for_status()
                return response.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                if attempt == 2: raise
                logger.warning(f"Request timeout/error (attempt {attempt+1}): {e}. Retrying...")
                await asyncio.sleep(2) # Non-blocking sleep
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

    async def _resolve_sheet_name(self, spreadsheet_id: str, target_name: str):
        """Resolves target_name to the actual sheet name in the spreadsheet (e.g. Sales vs Sale)"""
        cache_key = f"{spreadsheet_id}_{target_name}"
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key]

        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            spreadsheet = await self._execute_with_requests("GET", url)
            
            if not spreadsheet: return target_name
            
            sheets = [s.get("properties", {}).get("title") for s in spreadsheet.get("sheets", [])]
            
            logger.info(f"DEBUG: Found {len(sheets)} sheets in spreadsheet {spreadsheet_id}: {sheets}")
            
            # Cache ALL sheets for this spreadsheet
            for s in sheets:
                s_norm = s.strip().lower()
                self._sheet_cache[f"{spreadsheet_id}_{s}"] = s
                
                for t in ["Sales", "Purchases", "Expenses", "Payments"]:
                    t_norm = t.lower()
                    if s_norm == t_norm or s_norm == t_norm[:-1] or s_norm == t_norm + "s":
                         self._sheet_cache[f"{spreadsheet_id}_{t}"] = s

            if cache_key in self._sheet_cache:
                return self._sheet_cache[cache_key]

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
        
        return target_name

    @google_retry
    async def initialize_user_drive(self, business_name: str):
        """Idempotently sets up folder, 'Master_Ledger', and 'Invoice_Template' in user's Drive"""
        # 1. Check for existing Folder
        folder_name = f"Help U - {business_name}"
        loop = asyncio.get_event_loop()
        q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = await loop.run_in_executor(None, lambda: self.drive_service.files().list(q=q, fields="files(id)").execute())
        files = results.get("files", [])
        
        if files:
            folder_id = files[0]["id"]
            logger.info(f"Found existing folder: {folder_id} ({folder_name})")
        else:
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = await loop.run_in_executor(None, lambda: self.drive_service.files().create(body=folder_metadata, fields="id").execute())
            folder_id = folder.get("id")
            logger.info(f"Created new folder: {folder_id} ({folder_name})")

        # 2. Check for existing Master Ledger Sheet
        q = f"name = 'Master_Ledger' and parents in '{folder_id}' and trashed = false"
        results = await loop.run_in_executor(None, lambda: self.drive_service.files().list(q=q, fields="files(id)").execute())
        files = results.get("files", [])
        
        if files:
            sheet_id = files[0]["id"]
            logger.info(f"Found existing 'Master_Ledger': {sheet_id}")
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            spreadsheet = await self._execute_with_requests("GET", url)
            
            if spreadsheet:
                sheet_objs = spreadsheet.get("sheets", [])
                existing_sheets = [s.get("properties", {}).get("title") for s in sheet_objs]
                
                # Migration: 'Sheet1' -> 'Sales'
                if "Sheet1" in existing_sheets and "Sales" not in existing_sheets:
                    sheet1_id = next(s.get("properties", {}).get("sheetId") for s in sheet_objs if s.get("properties", {}).get("title") == "Sheet1")
                    batch_update_request = {
                        "requests": [{"updateSheetProperties": {"properties": {"sheetId": sheet1_id, "title": "Sales"}, "fields": "title"}}]
                    }
                    update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
                    await self._execute_with_requests("POST", update_url, body=batch_update_request)
                    existing_sheets = ["Sales" if s == "Sheet1" else s for s in existing_sheets]
                
                # Add missing sheets
                required_sheets = ["Sales", "Purchases", "Expenses", "Payments"]
                update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
                for s_name in required_sheets:
                    if s_name not in existing_sheets:
                        batch_update_request = {
                            "requests": [{"addSheet": {"properties": {"title": s_name}}}]
                        }
                        await self._execute_with_requests("POST", update_url, body=batch_update_request)
                        headers = self._get_payment_headers() if s_name == "Payments" else self._get_ledger_headers()
                        await self.append_to_master_ledger(sheet_id, headers, sheet_name=s_name)
                
                # Header Repair
                for s_name in ["Sales", "Purchases", "Expenses"]:
                    resolved_s_name = await self._resolve_sheet_name(sheet_id, s_name)
                    val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_s_name}'!A1:U1"
                    val_result = await self._execute_with_requests("GET", val_url)
                    current_headers = val_result.get("values", [[]])[0] if val_result else []
                    
                    target_headers = self._get_ledger_headers()
                    if len(current_headers) < len(target_headers):
                        update_val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_s_name}'!A1:U1"
                        params = {"valueInputOption": "USER_ENTERED"}
                        body = {"values": [target_headers]}
                        await self._execute_with_requests("PUT", update_val_url, body=body, params=params)
        else:
            sheet_metadata = {
                "name": "Master_Ledger",
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "parents": [folder_id]
            }
            sheet = await loop.run_in_executor(None, lambda: self.drive_service.files().create(body=sheet_metadata, fields="id").execute())
            sheet_id = sheet.get("id")
            
            # Initial setup with batchUpdate
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            spreadsheet = await self._execute_with_requests("GET", url)
            first_sheet_id = spreadsheet.get("sheets", [])[0].get("properties", {}).get("sheetId")
            
            batch_update_request = {
                "requests": [
                    {"updateSheetProperties": {"properties": {"sheetId": first_sheet_id, "title": "Sales"}, "fields": "title"}},
                    {"addSheet": {"properties": {"title": "Purchases"}}},
                    {"addSheet": {"properties": {"title": "Expenses"}}},
                    {"addSheet": {"properties": {"title": "Payments"}}}
                ]
            }
            update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
            await self._execute_with_requests("POST", update_url, body=batch_update_request)
            
            headers = self._get_ledger_headers()
            pay_headers = self._get_payment_headers()
            for s_name in ["Sales", "Purchases", "Expenses"]:
                await self.append_to_master_ledger(sheet_id, headers, sheet_name=s_name)
            await self.append_to_master_ledger(sheet_id, pay_headers, sheet_name="Payments")

        # 3. Invoice Template setup
        q = f"name = 'Invoice_Template' and parents in '{folder_id}' and trashed = false"
        results = await loop.run_in_executor(None, lambda: self.drive_service.files().list(q=q, fields="files(id)").execute())
        files = results.get("files", [])
        
        if files:
            doc_id = files[0]["id"]
        else:
            master_template_id = os.getenv("GOOGLE_INVOICE_TEMPLATE_ID")
            if master_template_id:
                doc_metadata = {"name": "Invoice_Template", "parents": [folder_id]}
                doc = await loop.run_in_executor(None, lambda: self.drive_service.files().copy(fileId=master_template_id, body=doc_metadata, fields="id").execute())
                doc_id = doc.get("id")
            else:
                doc_metadata = {
                    "name": "Invoice_Template",
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [folder_id]
                }
                doc = await loop.run_in_executor(None, lambda: self.drive_service.files().create(body=doc_metadata, fields="id").execute())
                doc_id = doc.get("id")
                # Add basic template content
                requests_body = {
                    "requests": [
                        {"insertText": {"location": {"index": 1}, "text": "{{ business_name }}\nGSTIN: {{ business_gstin }}\n\nTAX INVOICE\n\nInvoice No: {{ invoice_no }}\nDate: {{ date }}\n\nBill To:\n{{ customer_name }}\nGSTIN: {{ recipient_gstin }}\n\nDescription: Goods/Services\nHSN: {{ hsn_code }}\nRate: {{ gst_rate }}%\nTaxable Value: Rs. {{ taxable_value }}\n\nCGST: Rs. {{ cgst }}\nSGST: Rs. {{ sgst }}\nIGST: Rs. {{ igst }}\n\nTotal Amount: Rs. {{ total_amount }}\n"}}
                    ]
                }
                await loop.run_in_executor(None, lambda: self.docs_service.documents().batchUpdate(documentId=doc_id, body=requests_body).execute())

        return folder_id, sheet_id, doc_id

    async def append_to_master_ledger(self, sheet_id: str, row_data: list, sheet_name: str = "Sales"):
        """Appends a new transaction row to the Master Ledger Google Sheet using requests for stability"""
        return await self.batch_append_to_master_ledger(sheet_id, [row_data], sheet_name=sheet_name)

    async def batch_append_to_master_ledger(self, sheet_id: str, rows_data: list, sheet_name: str = "Sales"):
        """Appends multiple transaction rows to the Master Ledger in a single request for performance"""
        if not rows_data: return None
        
        start_time = time.time()
        resolved_name = await self._resolve_sheet_name(sheet_id, sheet_name)
        resolve_done = time.time()
        
        range_name = f"'{resolved_name}'!A:U"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}:append"
        params = {"valueInputOption": "USER_ENTERED"}
        body = {"values": rows_data}
        
        result = await self._execute_with_requests("POST", url, body=body, params=params)
        end_time = time.time()
        
        duration = end_time - start_time
        logger.info(f"  [TIMER] Google Sheet Batch Append ({sheet_name}, {len(rows_data)} rows): Total {duration:.2f}s (Resolve: {resolve_done - start_time:.2f}s, Append: {end_time - resolve_done:.2f}s)")
        
        return result

    @google_retry
    async def update_ledger_row(self, sheet_id: str, row_index: int, row_data: list, sheet_name: str = "Sales"):
        """Updates a specific row in the Master Ledger (row_index is 1-based)"""
        resolved_name = await self._resolve_sheet_name(sheet_id, sheet_name)
        range_name = f"'{resolved_name}'!A{row_index}:U{row_index}"
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"
        params = {"valueInputOption": "USER_ENTERED"}
        body = {"values": [row_data]}
        
        return await self._execute_with_requests("PUT", url, body=body, params=params)

    @google_retry
    async def get_last_ledger_row(self, sheet_id: str, sheet_name: str = "Sales"):
        """Returns the last data row and its 1-based index from the Master Ledger"""
        resolved_name = await self._resolve_sheet_name(sheet_id, sheet_name)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'{resolved_name}'!A:U"
        
        result = await self._execute_with_requests("GET", url)
        if not result:
            return None, None
            
        values = result.get("values", [])
        if not values or len(values) <= 1:
            return None, None
        return values[-1], len(values)

    async def generate_gstr1_json(self, sheet_id: str, gstin: str, fp: str):
        """Generates GSTR-1 compatible JSON from the Master Ledger"""
        gstin = str(gstin).strip().upper()
        
        rows = await self.get_ledger_rows(sheet_id, sheet_name="Sales")
        if not rows or len(rows) <= 1:
            return None

        target_month = fp[:2]
        target_year = fp[2:]

        data_rows = rows[1:]
        b2b_invoices = []
        b2cs_invoices = []
        hsn_data = []
        
        min_inv = None
        max_inv = None
        unique_invoices = set()
        
        for row in data_rows:
            if len(row) < 15: continue
                
            inv_date = str(row[3])
            if not inv_date or "-" not in inv_date: continue
                
            date_parts = inv_date.split("-")
            if len(date_parts) != 3: continue
                
            inv_month, inv_year = date_parts[1], date_parts[2]
            if inv_month != target_month or inv_year != target_year: continue

            inv_no = str(row[2]).strip().upper()
            unique_invoices.add(inv_no)
            
            if not min_inv or inv_no < min_inv: min_inv = inv_no
            if not max_inv or inv_no > max_inv: max_inv = inv_no

            inv_type = row[7]
            pos = str(row[5]).strip()
            if pos.isdigit() and len(pos) == 1: pos = f"0{pos}"
            elif not pos: pos = "37"

            if inv_type == "B2B":
                recipient_gstin = str(row[0]).strip().upper()
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

                vendor = next((v for v in b2b_invoices if v["ctin"] == recipient_gstin), None)
                if not vendor:
                    vendor = {"ctin": recipient_gstin, "inv": []}
                    b2b_invoices.append(vendor)
                
                invoice = next((i for i in vendor["inv"] if i["inum"] == inv_no), None)
                if invoice:
                    item_detail["num"] = len(invoice["itms"]) + 1
                    invoice["itms"].append(item_detail)
                    # Accumulate Total Invoice Value (Sum of line totals)
                    invoice["val"] = round(invoice["val"] + float(row[4] or 0), 2)
                else:
                    invoice = {
                        "inum": inv_no, "idt": row[3], "val": round(float(row[4] or 0), 2),
                        "pos": pos, "rchrg": row[6] or "N", "itms": [item_detail]
                    }
                    vendor["inv"].append(invoice)
            else:
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
                        "sply_ty": sply_ty, "pos": pos, "typ": "OE", "rt": rt,
                        "txval": round(float(row[14] or 0), 2), "iamt": round(float(row[17] or 0), 2),
                        "camt": round(float(row[15] or 0), 2), "samt": round(float(row[16] or 0), 2),
                        "csamt": round(float(row[18] or 0), 2)
                    })

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
                    "num": len(hsn_data) + 1, "hsn_sc": hsn_code, "desc": str(row[10] or "Goods/Services")[:30],
                    "uqc": uqc_code, "qty": round(float(row[12] or 1), 2), "val": round(float(row[4] or 0), 2),
                    "txval": round(float(row[14] or 0), 2), "iamt": round(float(row[17] or 0), 2),
                    "camt": round(float(row[15] or 0), 2), "samt": round(float(row[16] or 0), 2),
                    "csamt": round(float(row[18] or 0), 2)
                })

        total_docs = len(unique_invoices)
        return {
            "gstin": gstin, "fp": fp, "gt": 0.00, "cur_gt": 0.00,
            "b2b": b2b_invoices, "b2cs": b2cs_invoices, "hsn": {"data": hsn_data},
            "doc_issue": {"doc_det": [{"doc_num": 1, "docs": [{"from": min_inv or "N/A", "to": max_inv or "N/A", "totcnt": total_docs, "cancel": 0, "net_issue": total_docs}]}]}
        }

    async def generate_invoice_pdf_buffer(self, sheet_id: str, invoice_no: str, user_profile: dict = None):
        """Generates a PDF for a specific invoice number and returns it as a BytesIO buffer"""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        from io import BytesIO

        rows = await self.get_ledger_rows(sheet_id)
        if not rows or len(rows) <= 1:
            return None
            
        # Find all rows matching this invoice number
        invoice_rows = [row for row in rows[1:] if len(row) > 2 and row[2] == invoice_no]
        if not invoice_rows: return None
        
        # Use first row for general invoice metadata
        first_row = invoice_rows[0]

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2*cm, height-2*cm, user_profile.get("business_name", "My Business"))
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, height-2.6*cm, f"GSTIN: {user_profile.get('business_gstin', '')}")
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width/2, height-4*cm, "TAX INVOICE")
        
        # Details
        p.setFont("Helvetica", 11)
        p.drawString(2*cm, height-5*cm, f"Invoice No: {first_row[2]}")
        p.drawString(2*cm, height-5.6*cm, f"Date: {first_row[3]}")
        p.drawString(12*cm, height-5*cm, f"Bill To: {first_row[1]}")
        if len(first_row) > 0 and first_row[0]:
            p.drawString(12*cm, height-5.6*cm, f"GSTIN: {first_row[0]}")

        # Table Header
        y_pos = height-7*cm
        p.line(2*cm, y_pos, width-2*cm, y_pos)
        y_pos -= 0.5*cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2.2*cm, y_pos, "Description")
        p.drawString(8*cm, y_pos, "HSN")
        p.drawString(10*cm, y_pos, "Rate")
        p.drawString(12*cm, y_pos, "Taxable Value")
        p.drawString(16*cm, y_pos, "Total")
        y_pos -= 0.5*cm
        p.line(2*cm, y_pos, width-2*cm, y_pos)

        # Table Rows
        p.setFont("Helvetica", 10)
        total_taxable = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0
        grand_total = 0.0
        
        y_pos -= 0.6*cm
        for row in invoice_rows:
            if y_pos < 5*cm: # Basic pagination check
                p.showPage()
                y_pos = height - 2*cm
                p.setFont("Helvetica", 10)

            p.drawString(2.2*cm, y_pos, row[10] if len(row) > 10 else "Goods/Services")
            p.drawString(8*cm, y_pos, row[9] if len(row) > 9 else "")
            p.drawString(10*cm, y_pos, f"{row[13]}%" if len(row) > 13 else "0%")
            p.drawString(12*cm, y_pos, f"Rs. {row[14]}" if len(row) > 14 else "Rs. 0")
            p.drawString(16*cm, y_pos, f"Rs. {row[4]}" if len(row) > 4 else "Rs. 0")
            
            # Accumulate totals
            try:
                total_taxable += float(row[14] or 0)
                total_cgst += float(row[15] or 0)
                total_sgst += float(row[16] or 0)
                total_igst += float(row[17] or 0)
                grand_total += float(row[4] or 0)
            except: pass
            
            y_pos -= 0.6*cm

        # Summary
        y_pos -= 0.4*cm
        if y_pos < 6*cm:
            p.showPage()
            y_pos = height - 2*cm
            
        p.line(10*cm, y_pos, width-2*cm, y_pos)
        y_pos -= 0.6*cm
        p.drawString(11*cm, y_pos, "Taxable Value:")
        p.drawRightString(width-2.5*cm, y_pos, f"{total_taxable:.2f}")
        y_pos -= 0.6*cm
        p.drawString(11*cm, y_pos, "CGST:")
        p.drawRightString(width-2.5*cm, y_pos, f"{total_cgst:.2f}")
        y_pos -= 0.6*cm
        p.drawString(11*cm, y_pos, "SGST:")
        p.drawRightString(width-2.5*cm, y_pos, f"{total_sgst:.2f}")
        y_pos -= 0.6*cm
        p.drawString(11*cm, y_pos, "IGST:")
        p.drawRightString(width-2.5*cm, y_pos, f"{total_igst:.2f}")
        
        y_pos -= 1.0*cm
        p.setFont("Helvetica-Bold", 11)
        p.drawString(11*cm, y_pos, "Total Amount:")
        p.drawRightString(width-2.5*cm, y_pos, f"Rs. {grand_total:.2f}")

        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width/2, 2*cm, "This is a computer generated invoice.")
        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @google_retry
    async def get_ledger_rows(self, sheet_id: str, start_date: str = None, end_date: str = None, sheet_name: str = "Sales"):
        """Fetches all rows from the Master Ledger with optional date filtering"""
        try:
            from datetime import datetime
            resolved_name = await self._resolve_sheet_name(sheet_id, sheet_name)
            range_name = f"'{resolved_name}'!A1:U"
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"
            result = await self._execute_with_requests("GET", url)
            
            if not result: return []
            rows = result.get("values", [])
            if not rows or (not start_date and not end_date): return rows
                
            header, data_rows = rows[0], rows[1:]
            filtered_rows = [header]
            s_dt = datetime.strptime(start_date, "%d-%m-%Y") if start_date else None
            e_dt = datetime.strptime(end_date, "%d-%m-%Y") if end_date else None
            
            for row in data_rows:
                if len(row) >= 4:
                    try:
                        row_dt = datetime.strptime(row[3], "%d-%m-%Y")
                        if (s_dt and row_dt < s_dt) or (e_dt and row_dt > e_dt): continue
                    except: pass
                filtered_rows.append(row)
            return filtered_rows
        except Exception as e:
            logger.error(f"Error fetching ledger rows: {e}")
            return []

    async def get_ledger_stats(self, sheet_id: str, start_date: str = None, end_date: str = None):
        """Fetches and aggregates stats from Sales, Purchases, Expenses, and Payments sheets"""
        try:
            stats = {
                "count": 0, "total_sales": 0, "unpaid_sales": 0, "sales_count": 0,
                "total_purchases": 0, "unpaid_purchases": 0, "purchases_count": 0,
                "total_expenses": 0, "paid_expenses": 0, "unpaid_expenses": 0, "expenses_count": 0,
                "total_payments": 0, "payments_count": 0
            }
            
            # Sales
            sales_rows = await self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Sales")
            if len(sales_rows) > 1:
                data = sales_rows[1:]
                stats["sales_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_sales"] += val
                    if len(row) > 19 and row[19] == "Unpaid": stats["unpaid_sales"] += val
            
            # Purchases
            purchases_rows = await self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Purchases")
            if len(purchases_rows) > 1:
                data = purchases_rows[1:]
                stats["purchases_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_purchases"] += val
                    if len(row) > 19 and row[19] == "Unpaid": stats["unpaid_purchases"] += val
            
            # Expenses
            expenses_rows = await self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Expenses")
            if len(expenses_rows) > 1:
                data = expenses_rows[1:]
                stats["expenses_count"] = len(data)
                for row in data:
                    val = float(row[4] or 0)
                    stats["total_expenses"] += val
                    if len(row) > 19 and row[19] == "Unpaid": stats["unpaid_expenses"] += val
                    else: stats["paid_expenses"] += val

            # Payments
            payments_rows = await self.get_ledger_rows(sheet_id, start_date, end_date, sheet_name="Payments")
            if len(payments_rows) > 1:
                data = payments_rows[1:]
                stats["payments_count"] = len(data)
                for row in data:
                    stats["total_payments"] += float(row[1] or 0)

            stats["count"] = stats["sales_count"] + stats["purchases_count"] + stats["expenses_count"] + stats["payments_count"]
            return stats
        except Exception as e:
            logger.error(f"Error fetching ledger stats: {e}")
            return stats

    @google_retry
    async def upload_file_to_drive(self, folder_id: str, file_name: str, file_content: bytes, mime_type: str = "application/pdf"):
        """Uploads a file to a specific folder in Google Drive using MediaFileUpload"""
        import tempfile
        from googleapiclient.http import MediaFileUpload
        
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(file_content)
            temp_path = temp.name
            
        try:
            file_metadata = {"name": file_name, "parents": [folder_id]}
            media = MediaFileUpload(temp_path, mimetype=mime_type, resumable=True)
            
            loop = asyncio.get_event_loop()
            file = await loop.run_in_executor(None, lambda: self.drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute())
            return file.get("id"), file.get("webViewLink")
        finally:
            if os.path.exists(temp_path): os.remove(temp_path)

    async def get_business_summary(self, sheet_id: str):
        """Aggregates ledger data from all sheets into a summary for AI Consultant Agent"""
        from datetime import datetime, timedelta
        from collections import Counter
        
        today = datetime.now()
        this_month, last_month = today.strftime("%m-%Y"), (today.replace(day=1) - timedelta(days=1)).strftime("%m-%Y")
        
        summary = {
            "this_month": {"sales": 0, "purchases": 0, "expenses": 0, "gst_collected": 0, "gst_paid": 0},
            "last_month": {"sales": 0, "purchases": 0, "expenses": 0},
            "top_customers": Counter(), "top_vendors": Counter(), "overdue_payments": [], "total_unpaid": 0
        }
        
        # Scan Sales, Purchases, and Expenses
        for sheet_name in ["Sales", "Purchases", "Expenses"]:
            rows = await self.get_ledger_rows(sheet_id, sheet_name=sheet_name)
            if not rows or len(rows) <= 1: continue
            
            data_rows = rows[1:]
            for row in data_rows:
                if len(row) < 9: continue
                try:
                    val = float(row[4] or 0)
                    tx_type = row[8]
                    dt_str = row[3]
                    row_month = datetime.strptime(dt_str, "%d-%m-%Y").strftime("%m-%Y")
                    gst_total = float(row[15] or 0) + float(row[16] or 0) + float(row[17] or 0)
                    
                    if row_month == this_month:
                        if tx_type == "Sale":
                            summary["this_month"]["sales"] += val
                            summary["this_month"]["gst_collected"] += gst_total
                        elif tx_type == "Purchase":
                            summary["this_month"]["purchases"] += val
                            summary["this_month"]["gst_paid"] += gst_total
                        elif tx_type == "Expense":
                            summary["this_month"]["expenses"] += val
                    
                    elif row_month == last_month:
                        if tx_type == "Sale": summary["last_month"]["sales"] += val
                        elif tx_type == "Purchase": summary["last_month"]["purchases"] += val
                        elif tx_type == "Expense": summary["last_month"]["expenses"] += val
                    
                    entity_name = row[1]
                    if tx_type == "Sale": summary["top_customers"][entity_name] += val
                    else: summary["top_vendors"][entity_name] += val
                        
                    if len(row) > 19 and row[19] == "Unpaid":
                        summary["total_unpaid"] += val
                        if row[20] and row[20] != "N/A":
                            summary["overdue_payments"].append({"entity": entity_name, "amount": val, "due": row[20], "inv": row[2], "type": tx_type})
                except: continue
                
        summary["top_customers"] = dict(summary["top_customers"].most_common(3))
        summary["top_vendors"] = dict(summary["top_vendors"].most_common(3))
        return summary

    async def upload_bill_image(self, file_path: str, folder_id: str):
        """Uploads an image or PDF file to Google Drive"""
        start_time = time.time()
        if not os.path.exists(file_path): return None
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        
        mime_type = "image/jpeg"
        if file_name.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        elif file_name.lower().endswith(".png"):
            mime_type = "image/png"
            
        res = await self.upload_file_to_drive(folder_id, file_name, content, mime_type=mime_type)
        logger.info(f"  [TIMER] Google Drive Upload: {time.time() - start_time:.2f}s")
        return res

    async def generate_sales_invoice(self, template_id: str, data: dict, folder_id: str):
        """Generates a doc from template, replaces placeholders, and saves it in folder_id"""
        start_time = time.time()
        loop = asyncio.get_event_loop()
        copy_metadata = {"name": f"Invoice_{data.get('invoice_no', 'N/A')}", "parents": [folder_id]}
        doc = await loop.run_in_executor(None, lambda: self.drive_service.files().copy(fileId=template_id, body=copy_metadata, fields="id").execute())
        doc_id = doc.get("id")
        
        requests = []
        for key, value in data.items():
            requests.append({
                "replaceAllText": {
                    "containsText": {"text": "{{" + key + "}}", "matchCase": False},
                    "replaceText": str(value)
                }
            })
            
        if requests:
            await loop.run_in_executor(None, lambda: self.docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute())
        
        logger.info(f"  [TIMER] Google Doc Invoice Generation: {time.time() - start_time:.2f}s")
        return doc_id
