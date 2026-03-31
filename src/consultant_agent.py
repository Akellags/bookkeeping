import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ConsultantAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Fallback to gpt-4o-mini if env is not set
        self.model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        self.system_prompt = """
        Role: You are 'Help U Expert', a high-level Business Consultant for Indian Traders and SMEs.
        
        Context: You have access to a summary of the user's business data from their Google Sheets ledger.
        
        Your Goal:
        1. Analyze financial health (growth, cash flow, margins).
        2. Identify risks (overdue payments, high expenses).
        3. Provide GST compliance advice.
        4. Be proactive, conversational, and expert in your tone.
        
        Style Guidelines:
        - Use simple but professional language.
        - Use emojis to make reports readable.
        - Keep responses concise for WhatsApp (max 3-4 short paragraphs).
        - If the user asks for 'Analysis', provide a summary of their month.
        - If the user asks for 'Advice', answer their specific question using the data provided.
        """

    def analyze_business(self, summary: dict, user_query: str = "Provide a general business analysis"):
        """Sends business summary and query to OpenAI for expert interpretation"""
        try:
            prompt = f"User Query: {user_query}\n\nBusiness Summary Data:\n{summary}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in Consultant Agent analysis: {e}")
            return "I'm sorry, I'm having trouble analyzing your data right now. Please try again later."
