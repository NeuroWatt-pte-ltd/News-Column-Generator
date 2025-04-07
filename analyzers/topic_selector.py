import json
from typing import Dict, List, Any

from services import LLMService, PromptService, PromptCategory
from utils import setup_logger


class TopicSelector:
    """Select the most suitable topics for report generation"""
    
    def __init__(self, region: str, date: str):
        """
        Initialize topic selector
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        """
        self.region = region
        self.date = date
        self.logger = setup_logger("Topic Selector")
        
        # Initialize services
        self.llm_service = LLMService(
            temperature=0,
            model_name="gpt-4o",
            region=region
        )
        self.prompt_service = PromptService()
    
    async def select_topics(self, topics_data: List[Dict]) -> List[Dict]:
        """
        Select the most suitable topics for report generation
        
        :param topics_data: List of topic data
        :return: List of selected topics
        """
        self.logger.info("Selecting top topics")
        
        system_prompt = self.prompt_service.get_prompt(
            category=PromptCategory.TOPIC_SELECTION,
            prompt_name="system"
        )
        
        user_prompt = self.prompt_service.get_prompt(
            category=PromptCategory.TOPIC_SELECTION,
            prompt_name="user",
            topics_data=json.dumps(topics_data, ensure_ascii=False)
        )
        
        self.logger.debug(f"System Prompt: {system_prompt}")
        self.logger.debug(f"User Prompt: {user_prompt}")
        
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        self.logger.debug(f"Response: {response}")
        
        selected_topics = self._parse_topic_selection(response, topics_data)
        
        self.logger.info(f"Selected {len(selected_topics)} topics")
        
        return selected_topics
    
    def _parse_topic_selection(self, response: str, topics_data: List[Dict]) -> List[Dict]:
        """
        Parse topic selection response
        
        :param response: LLM response
        :param topics_data: Original topic data
        :return: List of selected topics
        """
        selected_topics = []
        try:
            lines = response.split('\n')
            current_topic = None
            
            for line in lines:
                if line.startswith('Topic ID:'):
                    if current_topic:
                        selected_topics.append(current_topic)
                    
                    # Extract topic ID and reason
                    parts = line.split(',', 1)
                    topic_id = parts[0].replace('Topic ID:', '').strip()
                    reason = parts[1].replace('Reason:', '').strip() if len(parts) > 1 else ''
                    
                    # Find corresponding topic data
                    topic_data = next(
                        (topic for topic in topics_data if str(topic.get('topic_id')) == topic_id),
                        None
                    )
                    
                    if topic_data:
                        current_topic = {
                            **topic_data,
                            'selection_reason': reason
                        }
            
            # Add the last topic
            if current_topic:
                selected_topics.append(current_topic)
                
            return selected_topics[:5]  # Ensure only 5 topics are returned
            
            
        except Exception as e:
            self.logger.error(f"Error parsing topic selection: {str(e)}")
            return []