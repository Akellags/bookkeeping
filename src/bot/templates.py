import re
import logging
from datetime import datetime
from src.gst_service import GSTLookupService

logger = logging.getLogger(__name__)

class TemplateHandler:
    def __init__(self):
        self.gst_service = GSTLookupService()

    @staticmethod
    def is_template(text: str) -> bool:
        """Checks if the message starts with a known template prefix"""
        if not text:
            return False
        first_line = text.split('\n')[0].strip().upper()
        return any(first_line.startswith(prefix + " |") for prefix in ["S", "P", "PMT", "EXP"])

    async def parse(self, text: str, product_master: dict = None) -> dict:
        """Parses a template-based message into a structured transaction JSON"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return None

        header = lines[0]
        parts = [p.strip() for p in header.split('|')]
        prefix = parts[0].upper()

        if prefix in ["S", "P"]:
            return await self._parse_sale_purchase(prefix, parts, lines[1:], product_master)
        elif prefix == "PMT":
            return self._parse_payment(parts)
        elif prefix == "EXP":
            return self._parse_expense(parts)
        
        return None

    async def _parse_sale_purchase(self, prefix, header_parts, item_lines, product_master: dict = None):
        """Handles S and P templates (Single and Multi-line)"""
        tx_type = "Sale" if prefix == "S" else "Purchase"
        product_master = product_master or {}
        
        # Determine if Single-Line or Multi-Line
        if not item_lines:
            # Single-Line Format: S/P | Party | Amount (Taxable) | GST% | Item | [GSTIN] | [Date] | [Invoice #] | [POS] | [UQC]
            party_name = header_parts[1] if len(header_parts) > 1 else "Unknown"
            taxable_value = float(header_parts[2]) if len(header_parts) > 2 else 0.0
            gst_rate = float(header_parts[3]) if len(header_parts) > 3 else 18.0
            item_name = header_parts[4] if len(header_parts) > 4 else "General Items"
            
            # Smart parsing for GSTIN vs Date at index 5
            gstin = ""
            date = datetime.now().strftime("%d-%m-%Y")
            
            if len(header_parts) > 5:
                val = header_parts[5]
                if self._is_gstin(val):
                    gstin = val
                elif self._is_date(val):
                    date = val
            
            if len(header_parts) > 6:
                val = header_parts[6]
                if self._is_date(val):
                    date = val
                elif not gstin and self._is_gstin(val):
                    gstin = val
            
            invoice_no = header_parts[7] if len(header_parts) > 7 else ""
            pos = header_parts[8] if len(header_parts) > 8 else ""
            uqc = header_parts[9] if len(header_parts) > 9 else "PCS"

            # Shortcode Lookup
            hsn = "OTH"
            lookup = product_master.get(item_name.upper())
            if lookup:
                item_name = lookup["description"]
                hsn = lookup["hsn_code"]
                # Use user provided rate if it looks intentional (not the default 18.0 or matches master)
                if len(header_parts) <= 3 or header_parts[3].strip() == "":
                    gst_rate = lookup["gst_rate"]
                uqc = lookup["uqc"]
            else:
                # Intelligent Discovery: If item_name is numeric, maybe it's an HSN?
                if item_name.isdigit() and len(item_name) >= 2:
                    gst_info = await self.gst_service.get_hsn_details(item_name)
                    if gst_info:
                        hsn = gst_info["hsn_code"]
                        item_name = gst_info["description"]
                        if len(header_parts) <= 3 or header_parts[3].strip() == "":
                            gst_rate = gst_info["gst_rate"]
                        uqc = gst_info["uqc"]
                else:
                    # Search by name
                    search_results = await self.gst_service.search_products(item_name)
                    if search_results:
                        top = search_results[0]
                        hsn = top["hsn_code"]
                        # Use discovery rate only if user didn't specify one
                        if len(header_parts) <= 3 or header_parts[3].strip() == "":
                            gst_rate = top["gst_rate"]
                        uqc = top.get("uqc", "PCS")

            # Calculate total from taxable
            total_amount = taxable_value * (1 + (gst_rate / 100))
            
            items = [{
                "hsn_code": hsn,
                "hsn_description": item_name,
                "quantity": 1,
                "unit_price": round(taxable_value, 2),
                "gst_rate": gst_rate,
                "taxable_value": round(taxable_value, 2),
                "total_amount": round(total_amount, 2),
                "uqc": uqc
            }]
        else:
            # Multi-Line Format
            # Header: S/P | Party | [GSTIN] | [Date] | [Invoice #] | [POS]
            party_name = header_parts[1] if len(header_parts) > 1 else "Unknown"
            
            gstin = ""
            date = datetime.now().strftime("%d-%m-%Y")
            
            if len(header_parts) > 2:
                val = header_parts[2]
                if self._is_gstin(val):
                    gstin = val
                elif self._is_date(val):
                    date = val
            
            if len(header_parts) > 3:
                val = header_parts[3]
                if self._is_date(val):
                    date = val
                elif not gstin and self._is_gstin(val):
                    gstin = val

            invoice_no = header_parts[4] if len(header_parts) > 4 else ""
            pos = header_parts[5] if len(header_parts) > 5 else ""
            
            items = []
            total_amount = 0.0
            for line in item_lines:
                # Item: Name (or Shortcode) | Qty | Unit Price | [GST%] | [UQC]
                i_parts = [p.strip() for p in line.split('|')]
                if len(i_parts) < 2: continue
                
                i_name = i_parts[0]
                qty = float(i_parts[1])
                
                # Shortcode Lookup
                hsn = "OTH"
                lookup = product_master.get(i_name.upper())
                if lookup:
                    i_name = lookup["description"]
                    price = float(i_parts[2]) if len(i_parts) > 2 else lookup["unit_price"]
                    rate = float(i_parts[3]) if len(i_parts) > 3 else lookup["gst_rate"]
                    uqc = lookup["uqc"]
                    hsn = lookup["hsn_code"]
                else:
                    price = float(i_parts[2]) if len(i_parts) > 2 else 0.0
                    rate = float(i_parts[3]) if len(i_parts) > 3 else 18.0
                    uqc = i_parts[4] if len(i_parts) > 4 else "PCS"
                    
                    # Discovery for Multi-line
                    if i_name.isdigit() and len(i_name) >= 2:
                        gst_info = await self.gst_service.get_hsn_details(i_name)
                        if gst_info:
                            hsn = gst_info["hsn_code"]
                            i_name = gst_info["description"]
                            if len(i_parts) <= 3: rate = gst_info["gst_rate"]
                            uqc = gst_info["uqc"]
                    else:
                        search_results = await self.gst_service.search_products(i_name)
                        if search_results:
                            top = search_results[0]
                            hsn = top["hsn_code"]
                            if len(i_parts) <= 3: rate = top["gst_rate"]
                            uqc = top.get("uqc", "PCS")
                
                i_taxable = qty * price
                i_total = i_taxable * (1 + (rate / 100))
                
                items.append({
                    "hsn_code": hsn,
                    "hsn_description": i_name,
                    "quantity": qty,
                    "unit_price": price,
                    "gst_rate": rate,
                    "taxable_value": round(i_taxable, 2),
                    "total_amount": round(i_total, 2),
                    "uqc": uqc
                })
                total_amount += i_total

        return {
            "is_transaction": True,
            "transaction_type": tx_type,
            "vendor_name": party_name if tx_type == "Purchase" else "",
            "recipient_name": party_name if tx_type == "Sale" else "",
            "vendor_gstin": gstin if tx_type == "Purchase" else "",
            "recipient_gstin": gstin if tx_type == "Sale" else "",
            "total_amount": round(total_amount, 2),
            "date": date,
            "invoice_no": invoice_no,
            "place_of_supply": pos,
            "items": items
        }

    def _parse_payment(self, parts):
        """PMT | Payee/Payer | Amount | Mode | [In/Out] | [Ref #] | [Date]"""
        payee = parts[1] if len(parts) > 1 else "Unknown"
        amount = float(parts[2]) if len(parts) > 2 else 0.0
        mode = parts[3] if len(parts) > 3 else "Cash"
        direction = parts[4] if len(parts) > 4 else "Out"
        ref_id = parts[5] if len(parts) > 5 else ""
        date = parts[6] if len(parts) > 6 else datetime.now().strftime("%d-%m-%Y")

        return {
            "is_transaction": True,
            "transaction_type": "Payment",
            "vendor_name": payee,
            "total_amount": round(amount, 2),
            "date": date,
            "payment_details": {
                "type": "Single",
                "mode": mode,
                "direction": direction,
                "reference_id": ref_id
            },
            "items": []
        }

    def _parse_expense(self, parts):
        """EXP | Category | Amount | [Notes] | [Date]"""
        category = parts[1] if len(parts) > 1 else "General"
        amount = float(parts[2]) if len(parts) > 2 else 0.0
        notes = parts[3] if len(parts) > 3 else ""
        date = parts[4] if len(parts) > 4 else datetime.now().strftime("%d-%m-%Y")

        return {
            "is_transaction": True,
            "transaction_type": "Expense",
            "vendor_name": category,
            "total_amount": round(amount, 2),
            "date": date,
            "notes": notes,
            "items": [{
                "hsn_description": category,
                "quantity": 1,
                "unit_price": amount,
                "gst_rate": 0,
                "taxable_value": round(amount, 2),
                "total_amount": round(amount, 2)
            }]
        }

    def _is_gstin(self, val: str) -> bool:
        """Returns True if the string looks like a GSTIN"""
        if not val: return False
        # GSTIN is 15 chars, alphanumeric
        pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        # Be a bit more lenient if needed, or just check length and basic alphanumeric
        return len(val) == 15 and re.match(r"^[0-9A-Z]{15}$", val.upper())

    def _is_date(self, val: str) -> bool:
        """Returns True if the string looks like a date (DD-MM-YYYY or DD/MM/YYYY)"""
        if not val: return False
        # Match common date patterns
        return bool(re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", val))
