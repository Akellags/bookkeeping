import csv
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GSTReportGenerator:
    @staticmethod
    def generate_gstr1_csv(ledger_rows):
        """
        Converts Ledger rows into a CSV formatted for the GSTR-1 Offline Tool.
        Expected Ledger Format: 
        GSTIN, Receiver Name, Invoice No, Date, Invoice Value, POS, Rev Charge, App %, Type, E-Comm, Rate, Taxable, Cess
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # GSTR-1 B2B/B2C Headers (simplified for MVP)
        headers = [
            "GSTIN/UIN of Recipient",
            "Receiver Name",
            "Invoice Number",
            "Invoice date",
            "Invoice Value",
            "Place Of Supply",
            "Reverse Charge",
            "Applicable % of Tax Rate",
            "Invoice Type",
            "E-Commerce GSTIN",
            "Rate",
            "Taxable Value",
            "Cess Amount"
        ]
        writer.writerow(headers)
        
        for row in ledger_rows:
            # We filter for 'Sale' types only for GSTR-1
            # Column I (index 8) is Transaction Type
            if len(row) >= 9 and row[8] == "Sale":
                # Ensure the row has 13 columns to match headers
                clean_row = row[:13]
                while len(clean_row) < 13:
                    clean_row.append("")
                writer.writerow(clean_row)
        
        return output.getvalue()

    @staticmethod
    def get_report_filename(whatsapp_id: str):
        month_year = datetime.now().strftime("%b_%Y")
        return f"GSTR1_{whatsapp_id}_{month_year}.csv"
