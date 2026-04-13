import json
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.extraction.orchestrator import ExtractionOrchestrator
from src.extraction.schemas import ExtractionRequest, ExtractionResult, CanonicalTransaction

class TestExtraction:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Ensure temp_media exists for tests
        if not os.path.exists("temp_media"):
            os.makedirs("temp_media")
            
        self.test_file = "temp_media/test_extract.txt"
        with open(self.test_file, "w") as f:
            f.write("Sample invoice text for testing.")
        
        yield
        
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @pytest.mark.asyncio
    @patch('src.extraction.openai_extractor.AsyncOpenAI')
    async def test_openai_extraction_flow(self, mock_openai_class):
        # Set default provider to openai
        os.environ["DEFAULT_EXTRACTION_PROVIDER"] = "openai"
        orchestrator = ExtractionOrchestrator()
        
        # Mocking OpenAI response
        mock_openai_instance = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "is_transaction": True,
            "transaction_type": "Purchase",
            "invoice_no": "INV-123",
            "date": "13-04-2026",
            "vendor_name": "Test Vendor",
            "total_amount": 1000.0
        })
        mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        req = ExtractionRequest(
            user_id="test_user",
            media_path=self.test_file,
            mime_type="text/plain",
            extraction_provider="openai"
        )
        
        result = await orchestrator.extract(req)
        
        assert isinstance(result, ExtractionResult)
        assert result.extraction_provider == "openai"
        assert result.canonical_data.invoice_no == "INV-123"
        assert result.canonical_data.total_amount == 1000.0

    @pytest.mark.asyncio
    @patch('src.extraction.google_extractor.GoogleDocumentAIClient')
    @patch('src.extraction.google_extractor.GoogleVertexAIClient')
    async def test_google_extraction_flow(self, mock_vertex_client_class, mock_docai_client_class):
        # Set dummy env vars for Google
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
        os.environ["DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"
        
        # Mock instances
        mock_docai_instance = mock_docai_client_class.return_value
        mock_vertex_instance = mock_vertex_client_class.return_value
        
        orchestrator = ExtractionOrchestrator()
        
        # Mock Document AI response (the client method)
        mock_doc = MagicMock()
        mock_doc.text = "Raw document text"
        mock_doc.entities = []
        mock_docai_instance.process_document = AsyncMock(return_value=mock_doc)
        
        # Mock Vertex AI response
        mock_vertex_instance.normalize_extraction = AsyncMock(return_value={
            "is_transaction": True,
            "transaction_type": "Sale",
            "invoice_no": "G-456",
            "date": "13-04-2026",
            "vendor_name": "Google Vendor",
            "total_amount": 2500.0
        })

        req = ExtractionRequest(
            user_id="test_user",
            media_path=self.test_file,
            mime_type="text/plain",
            extraction_provider="google"
        )
        
        result = await orchestrator.extract(req)
        
        assert result.extraction_provider == "google"
        assert result.canonical_data.invoice_no == "G-456"
        assert result.canonical_data.total_amount == 2500.0
