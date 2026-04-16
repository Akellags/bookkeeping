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
        # Use Gemini 2.5 Flash as the stable production-grade model
        self.model_name = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
        
        logger.info(f"Initializing Vertex AI: project={self.project_id}, location={self.location}, model={self.model_name}")
        vertexai.init(project=self.project_id, location=self.location)
        self.model = GenerativeModel(self.model_name)

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
        
        # List of models to try if the primary fails (latest models based on 2026 docs)
        candidate_models = [
            self.model_name,
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3.1-flash-preview",
            "gemini-1.5-flash-002"
        ]
        
        last_error = None
        for model_id in candidate_models:
            try:
                logger.info(f"Attempting normalization with model: {model_id}")
                temp_model = GenerativeModel(model_id)
                response = await temp_model.generate_content_async(
                    prompt,
                    generation_config=GenerationConfig(
                        response_mime_type="application/json"
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_id} failed: {e}")
                continue
                
        logger.error(f"All Vertex AI models failed. Last error: {last_error}")
        raise last_error
