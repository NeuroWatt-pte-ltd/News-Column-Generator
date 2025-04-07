import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from services import LLMService, TokenLimitError, PromptService, PromptCategory
from utils import setup_logger
from models import NewsArticle, Topic


class NewsFilterAnalyzer:
    """Analyze and filter news related to a topic"""
    
    def __init__(self, region: str, date: str):
        """
        Initialize news filter analyzer
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        """
        self.region = region
        self.date = date
        self.logger = setup_logger("News Filter")
        
        # Initialize services
        self.llm_service = LLMService(
            temperature=0,
            model_name="gpt-4o",
            region=region
        )
        self.prompt_service = PromptService()
    
    async def filter_related_news(self, topic: Union[Dict, Topic], news_list: List[Any]) -> List[NewsArticle]:
        """
        Filter news related to the topic
        
        :param topic: Topic object or dictionary
        :param news_list: News list (can be NewsArticle objects or dictionaries)
        :return: Filtered news list
        """
        try:
            # 獲取主題資訊
            if isinstance(topic, dict):
                topic_id = topic['topic_id']
                article_ids = topic['article_ids']
            else:
                topic_id = topic.topic_id
                article_ids = topic.article_ids
            
            self.logger.info(f"Filtering news for topic {topic_id}, found {len(article_ids)} related articles")
            
            # 使用 article_ids 直接找出相關新聞
            topic_related_news = []
            for news in news_list:
                news_id = str(news.id if isinstance(news, NewsArticle) else news.get('_id'))
                if news_id in article_ids:
                    if isinstance(news, NewsArticle):
                        topic_related_news.append(news)
                    else:
                        topic_related_news.append(NewsArticle.from_dict(news))
            
            if not topic_related_news:
                self.logger.warning(f"No news found for topic {topic_id}")
                return []
            
            self.logger.info(f"Found {len(topic_related_news)} news articles for topic {topic_id}")
            
            # 使用 LLM 進一步過濾
            simplified_news = [
                {
                    '_id': str(news.id),
                    'title': news.title,
                    'published_at': news.published_at.isoformat() if isinstance(news.published_at, datetime) else news.published_at,
                    'summary': news.summary
                }
                for news in topic_related_news
            ]
            
            # 呼叫 LLM 進行過濾
            system_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.NEWS_FILTERING,
                prompt_name="system"
            )

            self.logger.debug(f"System prompt: {system_prompt}")
            
            user_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.NEWS_FILTERING,
                prompt_name="user",
                topic_content=topic.content if isinstance(topic, Topic) else topic['content'],
                news_list=json.dumps(simplified_news, ensure_ascii=False)
            )
            self.logger.debug(f"User prompt: {user_prompt}")

            response = await self.llm_service.chat(system_prompt, user_prompt)
            self.logger.debug(f"LLM response: {response}")
            
            filtered_ids = self._parse_news_filtering(response, simplified_news)
            self.logger.debug(f"Filtered IDs: {filtered_ids}")
            
            # 返回過濾後的新聞
            final_news = []
            id_lookup = {str(news.id): news for news in topic_related_news}
            for article_id in filtered_ids:
                if article_id in id_lookup:
                    final_news.append(id_lookup[article_id])
            
            self.logger.info(f"After LLM filtering: {len(final_news)} news articles selected")
            return final_news
            
        except Exception as e:
            self.logger.error(f"Error filtering related news: {str(e)}")
            return topic_related_news[:10]  # 如果發生錯誤，返回前10篇相關新聞
    
    def _parse_news_filtering(self, response: str, news_list: List[Dict]) -> List[str]:
        """
        Parse news filtering response
        
        :param response: LLM response
        :param news_list: Original news list
        :return: List of filtered news IDs
        """
        filtered_ids = []
        try:
            # Build news ID mapping, map various possible ID formats to standardized IDs
            id_mapping = {}
            for news in news_list:
                news_id = str(news.get('_id', ''))
                id_mapping[news_id] = news_id
                
                # Handle possible MongoDB ObjectId format
                if isinstance(news.get('_id'), dict) and '$oid' in news.get('_id', {}):
                    oid = news.get('_id', {}).get('$oid', '')
                    id_mapping[oid] = news_id
                
                # Handle other possible ID formats
                if 'id' in news:
                    id_mapping[str(news.get('id', ''))] = news_id
            
            # Find all "Article ID:" lines
            lines = response.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if 'Article ID:' in line:
                    # Parse ID (possible format: Article ID: 123)
                    parts = line.split('Article ID:', 1)
                    if len(parts) > 1:
                        article_id = parts[1].strip().strip(',').strip(':').strip('"').strip("'")
                        article_id = article_id.split(' ')[0]  # Split in case there's other text after the ID
                        
                        if article_id in id_mapping:
                            filtered_ids.append(id_mapping[article_id])
                        else:
                            self.logger.warning(f"Cannot find article ID {article_id} in mapping: {id_mapping}")

            # If no specified format found, try to parse directly from JSON
            if not filtered_ids:
                try:
                    # Try to extract JSON portion from the response
                    json_start = response.find('{')
                    json_end = response.rfind('}')
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end+1]
                        json_data = json.loads(json_str)
                        
                        # Check different possible key names
                        possible_keys = ['selected_articles', 'filtered_news', 'relevant_articles', 'articles', 'ids']
                        for key in possible_keys:
                            if key in json_data and isinstance(json_data[key], list):
                                for item in json_data[key]:
                                    # Handle ID or complete news object
                                    if isinstance(item, str):
                                        article_id = item
                                    elif isinstance(item, dict) and '_id' in item:
                                        article_id = str(item['_id'])
                                    else:
                                        continue
                                        
                                    if article_id in id_mapping:
                                        filtered_ids.append(id_mapping[article_id])
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse JSON from response")
                except Exception as e:
                    self.logger.warning(f"Error processing JSON from response: {str(e)}")
                    
            # If still not found, try to find numeric identifiers
            if not filtered_ids:
                for line in lines:
                    # Look for "ID: nnn" or "#nnn" or numbered list format
                    patterns = [
                        r'ID:\s*(\d+)',
                        r'#(\d+)',
                        r'^(\d+)[.,)]'
                    ]
                    for pattern in patterns:
                        import re
                        matches = re.findall(pattern, line)
                        for match in matches:
                            article_id = match.strip()
                            if article_id in id_mapping:
                                filtered_ids.append(id_mapping[article_id])
            
            if not filtered_ids:
                self.logger.warning("No articles were filtered from the response")
                # If parsing fails, return all input news IDs as fallback
                return [str(news.get('_id', '')) for news in news_list]
            else:
                self.logger.info(f"Successfully filtered {len(filtered_ids)} articles")
                
            return filtered_ids
            
        except Exception as e:
            self.logger.error(f"Error parsing news filtering: {str(e)}")
            # If parsing fails, return all input news IDs as fallback
            return [str(news.get('_id', '')) for news in news_list] 