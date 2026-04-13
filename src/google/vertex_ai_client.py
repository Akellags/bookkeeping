import os
import logging
import json
from typing import Optional, Dict
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)

class GoogleVertexAIClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        vertexai.init(project=self.project_id, location=self.location)
        self.model = GenerativeModel("gemini-1.5-flash")

    async def normalize_extraction(self, raw_data: Dict, schema_prompt: str) -> Dict:
        """Uses Gemini to normalize raw extraction data into the canonical schema (Async)."""
        prompt = f"""
        You are a data normalization expert. Convert the following raw extraction data into a strict JSON format based on the canonical schema.
        
        Raw Data:
        {json.dumps(raw_data, indent=2)}
        
        Canonical Schema and Rules:
        {schema_prompt}
        
        Return ONLY the JSON object.
        """
        
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error normalizing data with Vertex AI: {e}")
            raise
