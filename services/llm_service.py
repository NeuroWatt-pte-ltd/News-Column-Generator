import os
from typing import Optional
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from utils import setup_logger


class LLMService:
    """Service for handling interactions with LLM models"""

    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0, region: Optional[str] = None):
        """
        Initialize the LLM service
        
        :param model_name: Name of the model to use
        :param temperature: Model temperature setting
        :param region: Region code, used for logging identification
        """
        self.logger = setup_logger(f"LLM Service")
        self.model = model_name
        self.temperature = temperature
        
        # Get API key from environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OPENAI_API_KEY is not set in environment variables."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=api_key)
        self.logger.debug(f"Initialized LLMService with model: {model_name}, temperature: {temperature}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=1, max=10))
    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Conduct a chat with the LLM
        
        :param system_prompt: System prompt text
        :param user_prompt: User prompt text
        :return: Model's response text
        """
        try:
            self.logger.debug("Sending chat request")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            error_msg = str(e)
            if "context_length_exceeded" in error_msg:
                # Raise specific exception for token limit errors
                raise TokenLimitError("Token limit exceeded")
            
            self.logger.warning(f"Error in chat request: {str(e)}")
            self.logger.info("Retrying...")
            raise


class TokenLimitError(Exception):
    """Token limit exceeded error"""
    pass