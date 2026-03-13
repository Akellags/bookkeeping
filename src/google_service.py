import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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
        self.drive_service = build("drive", "v3", credentials=self.creds)
        self.sheets_service = build("sheets", "v4", credentials=self.creds)
        self.docs_service = build("docs", "v1", credentials=self.creds)

    def initialize_user_drive(self):
        """Creates 'Help U' folder, 'Master_Ledger' sheet, and 'Invoice_Template' doc in user's Drive"""
        # 1. Create Help U Folder
        folder_metadata = {
            "name": "Help U",
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = self.drive_service.files().create(body=folder_metadata, fields="id").execute()
        folder_id = folder.get("id")

        # 2. Create Master Ledger Sheet inside the folder
        sheet_metadata = {
            "name": "Master_Ledger",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id]
        }
        sheet = self.drive_service.files().create(body=sheet_metadata, fields="id").execute()
        sheet_id = sheet.get("id")

        # 3. Initialize Sheet Headers (GSTR-1 Compliant)
        headers = [
            "Recipient GSTIN", "Receiver Name", "Invoice Number", "Invoice date", 
            "Invoice Value", "Place Of Supply", "Reverse Charge", "Invoice Type",
            "Transaction Type", "HSN Code", "HSN Description", "UQC", "Quantity", 
            "Rate", "Taxable Value", "CGST", "SGST", "IGST", "Cess Amount"
        ]
        self.append_to_master_ledger(sheet_id, headers)

        # 4. Create/Copy Invoice Template Doc
        master_template_id = os.getenv("GOOGLE_INVOICE_TEMPLATE_ID")
        if master_template_id:
            # Refined: Copy from master template if ID exists
            doc_metadata = {
                "name": "Invoice_Template",
                "parents": [folder_id]
            }
            doc = self.drive_service.files().copy(fileId=master_template_id, body=doc_metadata, fields="id").execute()
            doc_id = doc.get("id")
            logger.info(f"Copied invoice template from master: {master_template_id}")
        else:
            # Fallback: Create from scratch
            doc_metadata = {
                "name": "Invoice_Template",
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id]
            }
            doc = self.drive_service.files().create(body=doc_metadata, fields="id").execute()
            doc_id = doc.get("id")
            
            # Initialize Doc Template Content
            try:
                template_text = (
                    "{{ business_name }}\n"
                    "GSTIN: {{ business_gstin }}\n\n"
                    "TAX INVOICE\n\n"
                    "Invoice No: {{ invoice_no }}\n"
                    "Date: {{ date }}\n\n"
                    "Bill To:\n"
                    "{{ customer_name }}\n"
                    "GSTIN: {{ recipient_gstin }}\n\n"
                    "Description: Goods/Services\n"
                    "HSN: {{ hsn_code }}\n"
                    "Rate: {{ gst_rate }}%\n"
                    "Taxable Value: Rs. {{ taxable_value }}\n\n"
                    "CGST: Rs. {{ cgst }}\n"
                    "SGST: Rs. {{ sgst }}\n"
                    "IGST: Rs. {{ igst }}\n\n"
                    "Total Amount: Rs. {{ total_amount }}\n"
                )
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, 
                    body={"requests": [{"insertText": {"location": {"index": 1}, "text": template_text}}]}
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to initialize invoice template: {e}. Google Docs API might be disabled.")

        return folder_id, sheet_id, doc_id

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

    def append_to_master_ledger(self, sheet_id: str, row_data: list):
        """Appends a new transaction row to the Master Ledger Google Sheet"""
        range_name = "Sheet1!A:S" # Updated to S for 19 columns
        value_input_option = "USER_ENTERED"
        body = {
            "values": [row_data]
        }
        result = self.sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        return result

    def generate_gstr1_json(self, sheet_id: str, gstin: str, fp: str):
        """Generates GSTR-1 compatible JSON from the Master Ledger (B2B, B2CS, HSN, DOC)"""
        rows = self.get_ledger_rows(sheet_id)
        if not rows or len(rows) <= 1:
            return None

        # 19-Column Schema:
        # 0: Recipient GSTIN, 1: Receiver Name, 2: Invoice Number, 3: Invoice date, 
        # 4: Invoice Value, 5: Place Of Supply, 6: Reverse Charge, 7: Invoice Type,
        # 8: Transaction Type, 9: HSN Code, 10: HSN Description, 11: UQC, 12: Quantity, 
        # 13: Rate, 14: Taxable Value, 15: CGST, 16: SGST, 17: IGST, 18: Cess Amount

        data_rows = rows[1:]
        b2b_invoices = []
        b2cs_invoices = []
        hsn_data = []
        
        # Doc Summary trackers
        min_inv = None
        max_inv = None
        total_docs = 0
        
        for row in data_rows:
            if len(row) < 15 or row[8] != "Sale":
                continue
                
            total_docs += 1
            inv_no = row[2]
            if not min_inv or inv_no < min_inv: min_inv = inv_no
            if not max_inv or inv_no > max_inv: max_inv = inv_no

            inv_type = row[7]
            invoice_data = {
                "inum": row[2],
                "idt": row[3],
                "val": float(row[4] or 0),
                "pos": row[5] or "37",
                "rchrg": row[6] or "N",
                "itms": [{
                    "num": 1,
                    "itm_det": {
                        "rt": float(row[13] or 0),
                        "txval": float(row[14] or 0),
                        "camt": float(row[15] or 0),
                        "samt": float(row[16] or 0),
                        "iamt": float(row[17] or 0),
                        "csamt": float(row[18] or 0)
                    }
                }]
            }

            if inv_type == "B2B":
                recipient_gstin = row[0]
                inv_no = row[2]
                
                # Item detail for this row
                item_detail = {
                    "num": 1, # Will be updated later if needed
                    "itm_det": {
                        "rt": float(row[13] or 0),
                        "txval": float(row[14] or 0),
                        "camt": float(row[15] or 0),
                        "samt": float(row[16] or 0),
                        "iamt": float(row[17] or 0),
                        "csamt": float(row[18] or 0)
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
                    # Update total invoice value if it's stored per row but meant to be total
                    # Usually row[4] is the total invoice value, so it should be the same for all rows of the same invoice
                else:
                    invoice = {
                        "inum": inv_no,
                        "idt": row[3],
                        "val": float(row[4] or 0),
                        "pos": row[5] or "37",
                        "rchrg": row[6] or "N",
                        "itms": [item_detail]
                    }
                    vendor["inv"].append(invoice)
            else:
                pos = row[5] or "37"
                rt = float(row[13] or 0)
                sply_ty = "INTER" if float(row[17] or 0) > 0 else "INTRA"
                
                found_b2cs = False
                for b in b2cs_invoices:
                    if b["pos"] == pos and b["rt"] == rt:
                        b["txval"] += float(row[14] or 0)
                        b["iamt"] += float(row[17] or 0)
                        b["camt"] += float(row[15] or 0)
                        b["samt"] += float(row[16] or 0)
                        b["csamt"] += float(row[18] or 0)
                        found_b2cs = True
                        break
                
                if not found_b2cs:
                    b2cs_invoices.append({
                        "sply_ty": sply_ty,
                        "pos": pos,
                        "typ": "OE",
                        "rt": rt,
                        "txval": float(row[14] or 0),
                        "iamt": float(row[17] or 0),
                        "camt": float(row[15] or 0),
                        "samt": float(row[16] or 0),
                        "csamt": float(row[18] or 0)
                    })

            # HSN Summary (Table 12)
            hsn_code = row[9] or "OTH"
            found_hsn = False
            for h in hsn_data:
                if h["hsn_sc"] == hsn_code and h["uqc"] == (row[11] or "OTH"):
                    h["qty"] += float(row[12] or 1)
                    h["val"] += float(row[4] or 0)
                    h["txval"] += float(row[14] or 0)
                    h["iamt"] += float(row[17] or 0)
                    h["camt"] += float(row[15] or 0)
                    h["samt"] += float(row[16] or 0)
                    found_hsn = True
                    break
            if not found_hsn:
                hsn_data.append({
                    "num": len(hsn_data) + 1,
                    "hsn_sc": hsn_code,
                    "desc": row[10] or "Goods/Services",
                    "uqc": row[11] or "OTH",
                    "qty": float(row[12] or 1),
                    "val": float(row[4] or 0),
                    "txval": float(row[14] or 0),
                    "iamt": float(row[17] or 0),
                    "camt": float(row[15] or 0),
                    "samt": float(row[16] or 0),
                    "csamt": float(row[18] or 0)
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

    def get_ledger_rows(self, sheet_id: str, start_date: str = None, end_date: str = None):
        """Fetches all rows from the Master Ledger with optional date filtering"""
        try:
            from datetime import datetime
            range_name = "Sheet1!A1:S"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
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
        """Fetches and aggregates stats from the Master Ledger with optional date filtering"""
        try:
            from datetime import datetime
            rows = self.get_ledger_rows(sheet_id, start_date, end_date)
            if not rows or len(rows) <= 1:
                return {"count": 0, "total_sales": 0, "total_purchases": 0}
            
            data_rows = rows[1:]
            total_sales = 0
            total_purchases = 0
            count = len(data_rows)
            
            for row in data_rows:
                if len(row) >= 9:
                    invoice_value = float(row[4]) if row[4] else 0
                    transaction_type = row[8] # Column I is Transaction Type
                    
                    if transaction_type == "Sale":
                        total_sales += invoice_value
                    elif transaction_type == "Purchase":
                        total_purchases += invoice_value
                        
            return {
                "count": count,
                "total_sales": total_sales,
                "total_purchases": total_purchases
            }
        except Exception as e:
            logger.error(f"Error fetching ledger stats: {e}")
            return {"count": 0, "total_sales": 0, "total_purchases": 0}

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
