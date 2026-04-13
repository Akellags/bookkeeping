import os
import logging
from typing import Dict, Literal, Optional
from src.extraction.base import BaseExtractor
from src.extraction.openai_extractor import OpenAIExtractor
from src.extraction.google_extractor import GoogleExtractor
from src.extraction.schemas import ExtractionRequest, ExtractionResult

logger = logging.getLogger(__name__)

class ExtractionOrchestrator:
    def __init__(self):
        self.extractors: Dict[str, BaseExtractor] = {
            "openai": OpenAIExtractor(),
            "google": GoogleExtractor()
        }
        self.default_provider = os.getenv("DEFAULT_EXTRACTION_PROVIDER", "openai")

    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Routes the extraction request to the chosen provider."""
        provider = req.extraction_provider or self.default_provider
        
        if provider not in self.extractors:
            logger.warning(f"Unsupported provider '{provider}'. Falling back to '{self.default_provider}'.")
            provider = self.default_provider

        extractor = self.extractors[provider]
        logger.info(f"Using extractor: {provider} for user: {req.user_id}")
        
        try:
            return await extractor.extract(req)
        except Exception as e:
            logger.error(f"Extraction failed for provider {provider}: {e}")
            
            # Fallback logic: if Google fails, try OpenAI
            if provider == "google" and os.getenv("ENABLE_OPENAI_FALLBACK", "true").lower() == "true":
                logger.info("Retrying with OpenAI fallback...")
                req.extraction_provider = "openai"
                return await self.extractors["openai"].extract(req)
            
            raise

    def transcribe(self, audio_file_path: str) -> str:
        """Transcribes audio using the default transcription provider (currently OpenAI)."""
        # We know openai_extractor has this method
        openai_ext: OpenAIExtractor = self.extractors["openai"]
        return openai_ext.transcribe_audio(audio_file_path)
