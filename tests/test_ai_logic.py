import json
import unittest
from unittest.mock import MagicMock, patch
from src.ai_processor import AIProcessor

class TestAIProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = AIProcessor()

    @patch('src.ai_processor.OpenAI')
    def test_process_sales_text_parsing(self, mock_openai):
        # Mocking OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "transaction_type": "Sale",
            "invoice_no": "INV-001",
            "date": "23-02-2026",
            "vendor_name": "Apollo Pharm",
            "vendor_gstin": "36AAAAA0000A1Z5",
            "hsn_code": "9021",
            "taxable_value": 3000.00,
            "gst_rate": 12,
            "cgst": 180.00,
            "sgst": 180.00,
            "igst": 0.00,
            "total_amount": 3360.00
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        # Test input
        sales_text = "Bill for Apollo Pharm, 20 units Masks at 150 each, 12% GST."
        result = self.processor.process_sales_text(sales_text)

        # Assertions
        self.assertEqual(result['transaction_type'], 'Sale')
        self.assertEqual(result['total_amount'], 3360.00)
        self.assertEqual(result['vendor_name'], 'Apollo Pharm')

    def test_mock_ledger_row_conversion(self):
        # Sample AI Output
        ai_output = {
            "invoice_no": "INV-202",
            "date": "23-02-2026",
            "vendor_name": "Modern Traders",
            "vendor_gstin": "36BBBBB1111B1Z5",
            "taxable_value": 1000.00,
            "gst_rate": 18,
            "cgst": 90.00,
            "sgst": 90.00,
            "total_amount": 1180.00
        }
        
        # Expected Sheet Columns: 
        # GSTIN, Receiver Name, Invoice No, Date, Invoice Value, POS, Rev Charge, App %, Type, E-Comm, Rate, Taxable, Cess
        row = [
            ai_output.get("vendor_gstin"),
            ai_output.get("vendor_name"),
            ai_output.get("invoice_no"),
            ai_output.get("date"),
            ai_output.get("total_amount"),
            "36-Telangana", # Placeholder POS
            "N",
            ai_output.get("gst_rate"),
            "B2B",
            "",
            ai_output.get("gst_rate"),
            ai_output.get("taxable_value"),
            0.00
        ]
        
        self.assertEqual(len(row), 13)
        self.assertEqual(row[2], "INV-202")

if __name__ == "__main__":
    unittest.main()
