import os
import logging
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_asia_availability():
    load_dotenv()
    project_id = "help-u-488511"
    location = "asia-south1"
    model_name = "gemini-2.5-flash"
    
    logger.info(f"Checking {model_name} in {location}...")
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel(model_name)
        response = model.generate_content("Ping")
        print(f"SUCCESS: {model_name} is available in {location}!")
        return True
    except Exception as e:
        print(f"FAILED: {model_name} NOT found in {location}. Error: {str(e)[:100]}")
        return False

if __name__ == "__main__":
    check_asia_availability()
