from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from utils import setup_logger, get_config_loader, FileManager
from models import Topic, TopicStats, NewsArticle
from analyzers.topic_modeler import TopicModeler
from analyzers.topic_selector import TopicSelector



class TopicAnalyzer:
    """Topic analyzer, coordinates the topic analysis process"""
    
    def __init__(self, region: str, date: str):
        """
        Initialize topic analyzer
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        """
        self.region = region
        self.date = date
        self.logger = setup_logger("Topic Analyzer")
        
        # Initialize services and tools
        self.config_loader = get_config_loader()
        self.file_manager = FileManager()
        self.topic_modeler = TopicModeler(region=region)
        self.topic_selector = TopicSelector(region=region, date=date)
        
        self.logger.info(f"Initialized TopicAnalyzer for {region} on {date}")
    
    async def analyze_news(self, news_list: List[Union[Dict, NewsArticle]]) -> TopicStats:
        """
        Analyze news list, generate topics
        
        :param news_list: News list
        :return: Topic analysis result
        """
        try:
            if not news_list:
                self.logger.warning("Empty news list provided for analysis")
                return TopicStats()
            
            self.logger.info(f"Starting news analysis for {len(news_list)} articles")
            
            # Perform topic modeling (still returns dictionary format)
            topics_data_dict = await self.topic_modeler.perform_topic_modeling(news_list)
            
            if not topics_data_dict["topics"]:
                self.logger.warning("No topics generated from topic modeling")
                return TopicStats()
            
            # Convert to TopicStats object
            topics_stats = TopicStats.from_dict(topics_data_dict)
            
            # Save topic data (still using dictionary format to ensure backward compatibility)
            self.file_manager.save_topics(topics_data_dict, self.region, self.date)
            
            self.logger.info(f"Saved {len(topics_stats.topics)} topics")
            
            return topics_stats
            
        except Exception as e:
            self.logger.error(f"Error in news analysis: {str(e)}")
            return TopicStats()
    
    async def select_topics(self, topics_stats: TopicStats) -> List[Topic]:
        """
        Select topics most suitable for column generation
        
        :param topics_stats: Topic statistics data
        :return: List of selected topics
        """
        try:
            if not topics_stats or not topics_stats.topics:
                self.logger.warning("No topics provided for selection")
                return []
            
            self.logger.info(f"Selecting topics from {len(topics_stats.topics)} candidates")
            
            # Convert Topic objects to dictionaries for compatibility with selector
            topics_dicts = [topic.to_dict() for topic in topics_stats.topics]
            
            # Use topic selector to make selection (still using dictionary format)
            selected_topics_dicts = await self.topic_selector.select_topics(topics_dicts)
            
            # Convert back to Topic objects
            selected_topics = []
            for topic_dict in selected_topics_dicts:
                topic_id = topic_dict.get('topic_id')
                if topic_id is not None:
                    # Look for complete topic information in the original topic list
                    original_topic = topics_stats.get_topic_by_id(int(topic_id))
                    if original_topic:
                        # Set selection reason
                        original_topic.selection_reason = topic_dict.get('selection_reason', '')
                        selected_topics.append(original_topic)
                    else:
                        # If original topic not found, create new Topic object from dictionary
                        selected_topics.append(Topic.from_dict(topic_dict))
            
            self.logger.info(f"Selected {len(selected_topics)} topics")
            
            return selected_topics
            
        except Exception as e:
            self.logger.error(f"Error in topic selection: {str(e)}")
            return []
    
    async def generate_topics_from_news(self, news_list: List[Dict]) -> List[Topic]:
        """
        Generate topics from news list and select the most important ones
        
        :param news_list: News list
        :return: List of selected topics
        """
        try:
            # Analyze and generate topics
            topics_stats = await self.analyze_news(news_list)
            
            # Check if there are topics
            if not topics_stats.topics:
                self.logger.warning("No topics generated from news analysis")
                return []
            
            # Select topics
            selected_topics = await self.select_topics(topics_stats)
            
            return selected_topics
            
        except Exception as e:
            self.logger.error(f"Error generating topics from news: {str(e)}")
            return []