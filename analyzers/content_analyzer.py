import asyncio
from typing import Dict, List, Optional, Any, Union

from services import LLMService, PromptService, PromptCategory
from utils import setup_logger, get_config_loader
from reporting import ReportValidator
from models import NewsArticle, Topic



class ContentAnalyzer:
    """Generate report content"""
    
    def __init__(self, region: str, date: str):
        """
        Initialize the report content analyzer
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        """
        self.region = region
        self.date = date
        self.logger = setup_logger("Content Analyzer")
        
        # Initialize services
        self.llm_service = LLMService(
            temperature=0,
            model_name="gpt-4o",
            region=region
        )
        self.prompt_service = PromptService()
        
        # Initialize content validator
        self.validator = ReportValidator()
        
        # Use ConfigLoader to load configuration
        self.config_loader = get_config_loader()
        
        # Get language for the region from configuration
        self.source_lang = self.config_loader.get_region_language(region)
        self.logger.info(f"Initialized with region {region} and language {self.source_lang}")
    
    async def generate_report_content(self, topic: Union[Dict, Topic], filtered_news: List[Union[Dict, NewsArticle]]) -> Dict[str, str]:
        """
        Generate report content for a topic
        
        :param topic: Topic data (Topic object or dictionary)
        :param filtered_news: Filtered news list (list of NewsArticle objects or dictionaries)
        :return: Report content {'title': 'title', 'content': 'content'}
        """
        try:
            # 確保 topic 是 Topic 對象
            if isinstance(topic, dict):
                topic_content = topic.get('content', '')
                topic_id = topic.get('topic_id')
            else:
                topic_content = topic.content
                topic_id = topic.topic_id
            
            self.logger.info(f"Generating report for topic {topic_id}: {topic_content[:50]}...")
            
            # 提取相關新聞的摘要，優先使用有相同主題ID的新聞
            news_summaries = []
            for news in filtered_news:
                if isinstance(news, NewsArticle):
                    news_topics = news.topics
                    summary = news.summary or news.title
                else:
                    news_topics = news.get('topics', [])
                    summary = news.get('summary', '') or news.get('title', '')
                
                # 檢查新聞是否屬於當前主題
                is_relevant = False
                if news_topics:
                    for news_topic in news_topics:
                        if isinstance(news_topic, dict) and news_topic.get('topic_id') == topic_id:
                            is_relevant = True
                            break
                
                if is_relevant:
                    news_summaries.insert(0, summary)  # 相關新聞放在前面
                else:
                    news_summaries.append(summary)
            
            system_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.REPORT_GENERATION,
                prompt_name="system"
            )
            
            user_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.REPORT_GENERATION,
                prompt_name="user",
                news_summaries="\n\n".join(news_summaries),
                target_lang=self.source_lang
            )

            self.logger.debug(f"System Prompt: {system_prompt}")
            self.logger.debug(f"User Prompt: {user_prompt}")
            
            # Try up to 3 times
            for attempt in range(3):
                try:
                    response = await self.llm_service.chat(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt
                    )
                    self.logger.debug(f"Response: {response}")
                    
                    # Extract title and content from response
                    result = self.validator.extract_title_content(response)
                    
                    # Validate report format
                    if not self.validator.validate_report_format(result):
                        self.logger.warning(f"Invalid report format on attempt {attempt+1}/3")
                        continue
                    
                    # Validate word count
                    is_valid, reason, word_count = self.validator.validate_word_count(
                        result.get('content', ''), 
                        min_words=500, 
                        max_words=2000
                    )
                    
                    if not is_valid:
                        self.logger.warning(f"Invalid content length: {reason}, attempt {attempt+1}/3")
                        # If content is too long or too short but this is the last attempt, return result anyway
                        if attempt == 2:
                            self.logger.info(f"Returning report despite invalid length: {word_count} words")
                            return result
                        continue
                    
                    # If all validations pass, return the result
                    self.logger.info(f"Successfully generated report with {word_count} words")
                    return result
                        
                except Exception as e:
                    self.logger.warning(f"Report generation error on attempt {attempt+1}/3: {str(e)}")
                    
                    if attempt == 2:  # Last attempt
                        raise
            
            raise Exception("Failed to generate valid report after 3 attempts")
        except Exception as e:
            self.logger.error(f"Error generating report content: {str(e)}")
            raise