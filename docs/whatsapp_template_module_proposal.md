# Due Diligence: WhatsApp Template-Based Module

## 1. Executive Summary
To improve the reliability and speed of data entry via WhatsApp, we propose a **Fixed Template Module**. This module will allow users to submit Sale, Purchase, Payment, and Expense records using a structured "piped" format. This reduces the interaction from 3-4 steps to a single-step entry with one final confirmation.

## 2. The Problem with Free-Form Text
While the current AI-powered natural language processing is flexible, it faces challenges:
- **Ambiguity**: Users might omit crucial details, leading to follow-up questions.
- **Segues**: Casual conversation can confuse the intent detection.
- **Latency**: Multiple interaction steps (buttons/questions) increase the time to record a single entry.

## 3. Proposed Template Definitions

To ensure parity with the web dashboard, templates include both mandatory and optional fields. Optional fields are enclosed in `[]`.

### 💰 Sales (S) & 💸 Purchases (P)

#### Single Item Format
**Format**: `S/P | Party Name | Total Amount | GST% | Item Name | [GSTIN] | [Date] | [Invoice #] | [POS] | [UQC]`
- **POS**: Place of Supply (2-digit state code, e.g., 27 for Maharashtra).
- **UQC**: Unit (PCS, BOX, NOS, etc. Defaults to PCS).

**Example**: `S | Apollo Pharm | 1200 | 18 | Medicines | 27AAAAA0000A1Z5 | 04-05-2026 | INV-101 | 27 | PCS`

#### Multi-Item Format (New Line for each item)
When recording multiple items, use the first line for the **Header** and subsequent lines for **Items**. You can use **Shortcodes** (defined in Product Master) to skip entering prices and GST rates.

**Format**:
```text
S/P | Party Name | [GSTIN] | [Date] | [Invoice #] | [POS] | [Calc Type: TS/TI]
Shortcode | Qty
Description | Qty | Unit Price | GST% | [UQC]
```
- **Calc Type**: `TS` for Tax-Exclusive (default), `TI` for Tax-Inclusive.

**Example**:
```text
S | Sridhar | 36AAACY6329B1ZH | 01-05-2026 | INV-101 | TS
43MT | 2
Logitech Mouse | 5 | 600 | 12
```
*Note: 43MT is a shortcode. The bot pulls its price and GST from the Product Master. TS is the state code for Telangana.*

### 💳 Payments (PMT)
**Format**: `PMT | Payee/Payer | Amount | Mode | [In/Out] | [Ref #] | [Date]`
- **Mode**: Cash, UPI, Bank, Card.
- **In/Out**: Incoming (In) or Outgoing (Out). Defaults to Out.

**Example**:
```text
PMT | Sridhar | 25000 | UPI | Out | TXN12345 | 01-05-2026
```

### 🏠 Expenses (EXP)
**Format**: `EXP | Category | Amount | [Notes] | [Date]`
- **Category**: Rent, Bill, Salary, Tea, Internet, etc.

**Example**:
```text
EXP | Rent | 5000 | Office Rent Jan | 01-05-2026
```

## 4. The "One-Go" Workflow

### Phase 1: Interception
The `WhatsAppOrchestrator` or `handle_command` will check if the incoming text starts with a known template prefix (`S |`, `P |`, etc.). If detected, it bypasses general AI extraction and enters **Template Mode**.

### Phase 2: Structural Parsing
- **Deterministic**: The string is split by the `|` delimiter.
- **Mapping**: Fields are mapped directly to the GSTR-1 compliant JSON schema.
- **Validation**: A lightweight AI check (or regex validation) ensures numeric fields (Amount, GST%) are valid.

### Phase 3: Single-Click Confirmation
Instead of asking for Category, B2B/B2C, and Amount separately, the system presents a **single summary card**:
> 📝 **Template Parsed!**
> - **Type**: Sale
> - **Customer**: Apollo Pharm
> - **Amount**: ₹1,200 (18% GST)
> - **Item**: Medicines
>
> [ ✅ Confirm ] [ ❌ Edit ] [ 🗑️ Cancel ]

### Phase 4: Google Sheet Update
Upon confirmation, the `GoogleService` is called to append the row to the appropriate sheet (Sales, Purchases, etc.) in one atomic operation.

## 5. Module Architecture Plan
A new module `src/bot/templates.py` will be created to isolate this logic:
- `TemplateMatcher`: Detects the template pattern.
- `TemplateParser`: Handles the regex/split logic.
- `TemplateValidator`: Ensures data integrity before confirmation.

## 6. Benefits & Due Diligence Conclusion
- **High Accuracy**: Nearly 100% extraction accuracy for structured input.
- **Efficiency**: Reduces user effort and bot "chattiness".
- **Scalability**: New templates can be added without modifying core AI prompts.
- **Production Readiness**: This approach is significantly more robust for high-volume users.

**Recommendation**: Proceed with the implementation of the `src/bot/templates.py` module as a high-priority feature.
