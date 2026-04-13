import os
import logging
from typing import Optional
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions

logger = logging.getLogger(__name__)

class GoogleDocumentAIClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("DOCUMENT_AI_LOCATION", "us")
        self.processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        
        # Client options for the specific region
        self.client_options = ClientOptions(
            api_endpoint=f"{self.location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=self.client_options
        )

    async def process_document(self, file_path: str, mime_type: str) -> documentai.Document:
        """Sends a local file to Google Document AI for processing (Async)."""
        if not self.processor_id:
            raise ValueError("DOCUMENT_AI_PROCESSOR_ID environment variable is not set")

        # The full resource name of the processor
        name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"

        # Read the file into memory
        with open(file_path, "rb") as image:
            image_content = image.read()

        # Load Binary Data into Document AI RawDocument Object
        raw_document = documentai.RawDocument(
            content=image_content, mime_type=mime_type
        )

        # Configure the process request
        request = documentai.ProcessRequest(
            name=name, raw_document=raw_document
        )

        # Use the Document AI client to process the document
        try:
            result = await self.client.process_document(request=request)
            return result.document
        except Exception as e:
            logger.error(f"Error processing document with Document AI: {e}")
            raise
