# GST Intelligence: HSN & SAC Implementation Guide

This document provides examples and use cases for the **Harmonized System of Nomenclature (HSN)** for goods and **Services Accounting Code (SAC)** for services within the HelpU Bookkeeper ecosystem.

---

## 1. Core Concepts
*   **HSN (8 digits)**: Used for physical products (e.g., Laptops, Medicines).
*   **SAC (6 digits)**: Used for professional or operational services (e.g., Legal fees, Rent).
*   **Drill-down**: Start with a broad category (4 digits) and refine to the exact 8-digit code required for compliance.

---

## 2. Frontend Use Cases (Product Master)

### Use Case: Adding a New Product (Good)
1.  **Action**: User enters `LAPTOP` in the Description and clicks **Search/Verify**.
2.  **Result**: Modal displays:
    *   `HSN: 84713010` - Personal Computer (Laptop)
    *   `Rate: 18%`
3.  **Selection**: Clicking the result automatically populates the row.

### Use Case: Adding an Expense (Service)
1.  **Action**: User enters `OFFICE RENT` and clicks **Search/Verify**.
2.  **Result**: Modal displays:
    *   `SAC: 997212` - Real estate services of own or leased property
    *   `Rate: 18%`
3.  **Selection**: Populates the code as `997212` and sets the rate.

---

## 3. WhatsApp Template Use Cases

### Deterministic Sale (Single Item)
Users can now use shortcodes or full descriptions. The bot identifies if it's a good or service.

**Format**: `S | Party | Amount | GST | Description`

*   **Example (Good)**:
    `S | Apollo Pharm | 1200 | 18 | Medicines`
    *   *Bot Action*: Checks Master Ledger for "Medicines". If not found, uses HSN Discovery (FastGST) to find code `3004`.

*   **Example (Service)**:
    `S | Tech Corp | 50000 | 18 | Software Consulting`
    *   *Bot Action*: Uses SAC Discovery to find code `998311` (Management consulting and IT services).

---

## 4. GSTR-1 Compliance Logic

Our system automatically separates HSN and SAC in the background for reporting:
1.  **B2B/B2C**: If the code starts with `99`, it is flagged as a **Service (SAC)**.
2.  **Tax Split**: Based on the **Place of Supply (POS)** and the discovered rate, IGST or CGST/SGST is calculated.
3.  **JSON Generation**: The GSTR-1 JSON generator groups items into the `hsn_sum` (HSN Summary) section, ensuring both Goods and Services are reported accurately to the government portal.

---

## 6. Bulk Import (CSV Format)
For businesses with many products, use the **Import CSV** feature in the Product Master. The CSV must have the following headers (order matters):

`Shortcode, Description, HSN_Code, GST_Rate, UQC, Unit_Price`

### Example CSV Content:
```csv
Shortcode,Description,HSN_Code,GST_Rate,UQC,Unit_Price
IPHONE15,iPhone 15 Pro Max 256GB,85171300,18,PCS,125000
MBP14,MacBook Pro 14 M3,84713010,18,PCS,169000
CONSULT,Software Development Services,998314,18,HR,5000
```

---

## 7. Pro Tip for Users
> **Pro Tip**: If you know your 4-digit HSN or SAC code, type it directly in the code field and click search. We will drill down into the sub-categories for you!
