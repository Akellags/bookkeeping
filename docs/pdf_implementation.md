# PDF Implementation for Future

## Overview
Currently, the system only supports image-based transaction extraction. To support native and scanned PDF invoices, we need to implement a conversion or extraction layer before calling the AI.

## Implementation Steps

1. **Add Dependencies**:
   - `pdf2image`: For converting PDF pages into images for the Vision API.
   - `Poppler`: System-level dependency for PDF rendering.
   - `PyMuPDF (fitz)`: Alternative for high-speed text and layout extraction.

2. **Modify Backend (`src/main.py`)**:
   - Update `/api/transactions/process-image` to detect `application/pdf` MIME types.
   - For PDFs:
     - Convert the first page (or all pages) to a high-resolution JPEG.
     - Pass the converted image(s) to the existing `AIProcessor`.

3. **Enhance AI Processor (`src/ai_processor.py`)**:
   - Create a specialized `process_pdf_invoice` method.
   - For digitally readable PDFs, consider extracting text metadata first to reduce token costs.

4. **Frontend Updates**:
   - Allow `.pdf` file selection in the `TransactionModal`.
   - Update file upload validation to support PDFs.

## Pros & Cons of PDF-to-Image for OpenAI Vision

### Pros
- **High Accuracy for Tables**: Vision models are excellent at "seeing" the layout of complex GST invoices, which simple text extraction often fails to parse correctly.
- **Scanned Support**: Handles both digitally-born PDFs and scanned photos/documents without needing separate logic.
- **Spatial Context**: Preserves the relationship between labels and values (e.g., "Total Amount" next to its value).

### Cons
- **Token Usage**: Images consume significantly more tokens than raw text extraction.
- **Latency**: Converting PDFs to images adds a few seconds of server-side processing time.
- **Dependency Heavy**: Requires system-level libraries like Poppler/Ghostscript, which complicates deployment (Docker is recommended).
- **OCR Risks**: Native PDFs have 100% accurate text data; converting them to images introduces a tiny risk of OCR misreading (e.g., 'O' vs '0').
