import os
import logging
import asyncio
from src.google.vertex_ai_client import GoogleVertexAIClient

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        """Initializes Vertex AI client for transcription"""
        self.vertex_ai = GoogleVertexAIClient()

    async def transcribe_audio(self, audio_file_path: str):
        """Transcribes local audio file using Gemini Multimodal (Async)"""
        try:
            # WhatsApp often sends .ogg (Opus) or .m4a; Gemini supports these
            # We need to determine the correct mime type
            ext = os.path.splitext(audio_file_path)[1].lower()
            mime_type = "audio/ogg" if ext == ".ogg" else "audio/mpeg"
            if ext == ".m4a": mime_type = "audio/mp4"

            prompt = "Transcribe this audio accurately. If it's in a language other than English, transcribe it as is (do not translate)."

            logger.info(f"Transcribing audio with Gemini: {audio_file_path} (Mime: {mime_type})")
            
            from vertexai.generative_models import Part
            with open(audio_file_path, "rb") as f:
                file_data = f.read()
            part = Part.from_data(data=file_data, mime_type=mime_type)
            
            response = await self.vertex_ai.model.generate_content_async([part, prompt])
            full_text = response.text.strip()
            
            logger.info(f"Successfully transcribed audio with Gemini: {full_text}")
            return full_text, "unknown"
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Gemini: {e}")
            return None, None
