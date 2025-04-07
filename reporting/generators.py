import os
import json
import asyncio
from datetime import datetime
import pytz
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re
import traceback

from models import NewsArticle, Topic, TopicStats, Report
from services import LLMService, PromptService
from analyzers import NewsFilterAnalyzer, ContentAnalyzer, TopicAnalyzer
from analyzers.topic_selector import TopicSelector
from utils import setup_logger, get_config_loader, PathManager
from reporting import ReportValidator, ReportFormatter


class BaseReportGenerator:
    """Report generator implementing common report generation logic"""
    
    def __init__(self, date: str, region: str):
        """
        Initialize report generator
        
        :param date: Date string (YYYYMMDD)
        :param region: Region code (tw/us/vt)
        """
        self.date = date
        self.region = region
        
        # Initialize logger
        self.logger = setup_logger(f"Generators-{region}")
        
        # Use ConfigLoader to load configuration
        self.config_loader = get_config_loader()
        
        # Get language for the region from configuration
        self.source_lang = self.config_loader.get_region_language(region)
        
        # Get weighted source settings
        region_info = self.config_loader.get_region_info(region)
        self.weighted_sources = region_info.get('weighted_sources', {})
        
        # Initialize services
        self.llm_service = LLMService(
            temperature=0,
            model_name="gpt-4o",
            region=self.region 
        )
        self.prompt_service = PromptService()
        
        # Set paths (using PathManager)
        PathManager.ensure_dir(PathManager.get_output_base(region, date))
        self.output_path = PathManager.get_reports_path(region, date)
        
        # Initialize analyzers
        self.topic_selector = TopicSelector(region=region, date=date)
        self.news_filter = NewsFilterAnalyzer(region=region, date=date)
        self.content_analyzer = ContentAnalyzer(region=region, date=date)
        
        # Initialize other tools
        self.validator = ReportValidator()
        self.formatter = ReportFormatter(region=region)  # Using ReportFormatter from reporting.formatters
    
    async def select_topics(self, topics_data: TopicStats) -> List[Topic]:
        """
        Select topics most suitable for report generation
        
        :param topics_data: Topic data
        :return: List of selected topics
        """
        self.logger.info("Selecting top topics")
        
        # Convert to format expected by TopicAnalyzer
        topic_analyzer = TopicAnalyzer(region=self.region, date=self.date)
        selected_topics = await topic_analyzer.select_topics(topics_data)
        
        return selected_topics
    
    async def filter_related_news(self, topic_content: str, news_list: List[Union[Dict, NewsArticle]]) -> List[NewsArticle]:
        """
        Filter news related to the topic
        
        :param topic_content: Topic content
        :param news_list: News list
        :return: Filtered news list
        """
        try:
            # Use news_filter to filter news
            filtered_news = await self.news_filter.filter_related_news(
                topic_content=topic_content,
                news_list=news_list
            )
            
            return filtered_news
            
        except Exception as e:
            self.logger.error(f"Error filtering related news: {str(e)}")
            # Convert dictionaries to NewsArticle objects
            normalized_news_list = []
            for news in news_list:
                if isinstance(news, NewsArticle):
                    normalized_news_list.append(news)
                else:
                    normalized_news_list.append(NewsArticle.from_dict(news))
            
            # Sort by time and return the latest 10 news as fallback
            sorted_news = sorted(
                normalized_news_list,
                key=lambda x: x.published_at if x.published_at else "",
                reverse=True
            )
            return sorted_news[:10]
    
    async def process_topic(self, topic: Topic, news_list: List[Union[Dict, NewsArticle]]) -> Optional[Report]:
        """
        Process a single topic
        
        :param topic: Topic to process
        :param news_list: List of news articles
        :return: Generated report or None if processing failed
        """
        try:
            topic_id = topic.topic_id
            self.logger.info(f"Processing topic {topic_id}: {topic.content[:50]}...")
            
            # Filter related news
            filtered_news = await self.news_filter.filter_related_news(
                topic=topic,
                news_list=news_list
            )
            
            if not filtered_news:
                self.logger.warning(f"No related news found for topic {topic_id}")
                return None
            
            # Record used article IDs
            used_article_ids = [
                news.id if isinstance(news, NewsArticle) else news.get('_id')
                for news in filtered_news
            ]
            topic.article_ids = used_article_ids
            
            # Update topic counts
            topic.count = len(filtered_news)
            topic.weighted_count = sum(
                self.weighted_sources.get(
                    news.source if isinstance(news, NewsArticle) else news.get('source', ''),
                    1.0
                )
                for news in filtered_news
            )
            
            # 1. Generate report content
            report_content = await self.content_analyzer.generate_report_content(topic, filtered_news)
            if not report_content or not report_content.get('content'):
                self.logger.warning(f"Failed to generate report content for topic {topic_id}, using fallback content")
                # Use fallback content instead of returning None
                report_content = {
                    'title': getattr(topic, 'title', f"Topic {topic_id}"),
                    'content': f"This is a placeholder report for topic {topic_id}. The original content generation failed. " +
                               f"This topic is about {topic.content}."
                }
            
            # 2. Validate report content
            content_valid, reason, word_count = await self.validator.validate_content(
                content=report_content.get('content', ''),
                title=report_content.get('title', ''),
                min_words=500,
                max_words=2000
            )
            
            # If content validation fails, regenerate
            retry_count = 0
            while not content_valid and retry_count < 3:
                self.logger.warning(f"Content validation failed: {reason}. Retrying...")
                retry_count += 1
                
                # Regenerate report content
                report_content = await self.content_analyzer.generate_report_content(topic, filtered_news)
                if not report_content or not report_content.get('content'):
                    self.logger.warning(f"Failed to regenerate report content for topic {topic_id}, using last valid content or fallback")
                    # If there was valid content before, use that; otherwise use fallback content
                    if not report_content:
                        report_content = {
                            'title': getattr(topic, 'title', f"Topic {topic_id}"),
                            'content': f"This is a placeholder report for topic {topic_id} after failed retry. " +
                                      f"This topic is about {topic.content}."
                        }
                    # Don't return None, ensure there's content to proceed with
            
            if not content_valid:
                self.logger.warning(f"Content validation failed after {retry_count} retries: {reason}")
                # Regardless of what caused the validation to fail, continue with the last generated content
                self.logger.info(f"Proceeding with the last generated content despite validation issues: {reason}")
            
            # Compile final report (first get dictionary using formatter, then convert to Report object)
            report_dict = self.formatter.compile_report(
                topic=topic.to_dict(),
                report_content=report_content,
                filtered_news=[news.to_dict() if isinstance(news, NewsArticle) else news for news in filtered_news],
                sentiment_analysis={},  # Empty sentiment analysis result
                source_lang=self.source_lang
            )
            
            # Convert to Report object
            report = Report.from_dict(report_dict)
            
            self.logger.info(f"Successfully processed topic {topic_id}")
            return report
        
        except Exception as e:
            # Safely try to get topic_id
            topic_id = getattr(topic, 'topic_id', 'unknown')
            self.logger.error(f"Error processing topic {topic_id}: {str(e)}")
            return None
    
    async def execute(self) -> List[Report]:
        """
        Execute report generation process
        
        :return: List of generated reports
        """
        try:
            # 1. Load news data
            self.logger.info("Loading news data...")
            news_list = self._load_news_data()
            
            if not news_list:
                self.logger.error("No news data found, cannot proceed with report generation")
                return []
            
            # 2. Use topic analyzer for topic modeling and selection
            self.logger.info("Analyzing news and generating topics...")
            topic_analyzer = TopicAnalyzer(region=self.region, date=self.date)
            
            # Perform topic modeling
            topics_data = await topic_analyzer.analyze_news(news_list)
            
            if not topics_data or not topics_data.topics:
                self.logger.warning("No topics generated from news analysis")
                return []
            
            # Save news with topics
            self._save_news_with_topics(news_list, topics_data)
            
            # 3. Select topics
            self.logger.info("Selecting top topics...")
            selected_topics = await topic_analyzer.select_topics(topics_data)
            
            if not selected_topics:
                self.logger.warning("No topics selected for report generation")
                return []
            
            # 4. Process multiple topics in parallel
            self.logger.info(f"Processing {len(selected_topics)} topics in parallel...")
            tasks = [self.process_topic(topic, news_list) for topic in selected_topics]
            reports_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 5. Filter out exceptions and None results
            reports = []
            for i, result in enumerate(reports_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing topic {selected_topics[i].topic_id}: {str(result)}")
                elif result is not None:
                    reports.append(result)
            
            # 6. Save reports
            if reports:
                self._save_reports(reports)
                self.logger.info(f"Successfully generated and saved {len(reports)} reports")
            else:
                self.logger.warning("No reports were generated")
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Error in report generation: {str(e)}")
            traceback.print_exc()
            raise
    
    async def _perform_topic_modeling(self, news_list: List[Union[Dict, NewsArticle]]) -> List[Topic]:
        """
        Perform topic modeling analysis
        
        :param news_list: List of news articles
        :return: List of topics
        """
        try:
            # Use TopicAnalyzer for topic modeling
            topic_analyzer = TopicAnalyzer(region=self.region, date=self.date)
            
            # Perform topic modeling
            topics_stats = await topic_analyzer.analyze_news(news_list)
            
            # Return topic list
            return topics_stats.topics
        except Exception as e:
            self.logger.error(f"Error in topic modeling: {str(e)}")
            return []
    
    def _save_topics_data(self, topics_data: TopicStats) -> None:
        """
        Save topic data
        
        :param topics_data: Topic statistics data
        """
        try:
            topics_path = PathManager.get_topics_path(self.region, self.date)
            PathManager.ensure_dir(topics_path.parent)
            
            # Convert TopicStats object to dictionary
            topics_dict = topics_data.to_dict()
            
            with open(topics_path, 'w', encoding='utf-8') as f:
                json.dump(topics_dict, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Topics data saved to {topics_path}")
        except Exception as e:
            self.logger.error(f"Error saving topics data: {str(e)}")
    
    def _load_topics_data(self) -> TopicStats:
        """
        Try to load existing topic data, return empty TopicStats if not found
        
        :return: Topic statistics data
        """
        try:
            # Use PathManager to get topic data file path
            file_path = PathManager.get_topics_path(self.region, self.date)
            
            if not file_path.exists():
                self.logger.warning(f"Topics data file not found: {file_path}")
                return TopicStats()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to TopicStats object
            return TopicStats.from_dict(data)
        except Exception as e:
            self.logger.warning(f"Error loading topics data, will generate new topics: {str(e)}")
            return TopicStats()
    
    def _load_news_data(self) -> List[NewsArticle]:
        """
        Read news data (using PathManager)
        
        :return: List of news articles
        """
        try:
            # Use PathManager to get news data file path
            news_file = PathManager.get_news_input_path(self.region, self.date)
            
            if not news_file.exists():
                self.logger.error(f"News file not found: {news_file}")
                return []
                
            with open(news_file, 'r', encoding='utf-8') as f:
                news_dicts = json.load(f)
            
            # Convert dictionaries to NewsArticle objects
            return [NewsArticle.from_dict(news_dict) for news_dict in news_dicts]
        except Exception as e:
            self.logger.error(f"Error loading news data: {str(e)}")
            return []
    
    def _save_reports(self, reports: List[Report]) -> None:
        """
        Save reports to file (using PathManager)
        
        :param reports: List of reports to save
        """
        try:
            # Use PathManager to ensure directory exists
            path = Path(self.output_path)
            PathManager.ensure_dir(path.parent)
            
            # Convert Report objects to dictionaries
            report_dicts = [report.to_dict() for report in reports]
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dicts, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Reports saved to {self.output_path}")
        except Exception as e:
            self.logger.error(f"Error saving reports: {str(e)}")
            raise
    
    def _save_news_with_topics(self, news_list: List[NewsArticle], topics_data: TopicStats) -> None:
        """
        Save news articles with their assigned topics
        
        :param news_list: List of news articles
        :param topics_data: Topic statistics data
        """
        try:
            # Create a mapping of article IDs to their topics
            article_topics = {}
            for topic in topics_data.topics:
                topic_info = {
                    'topic_id': topic.topic_id,
                    'topic_content': topic.content,
                    'topic_keywords': topic.keywords,
                    'topic_weight': topic.weighted_count
                }
                # Add this topic info to all articles that belong to this topic
                for article_id in topic.article_ids:  # 使用新增的 article_ids 屬性
                    if article_id not in article_topics:
                        article_topics[article_id] = []
                    article_topics[article_id].append(topic_info)

            # Add topics to news articles
            news_with_topics = []
            for article in news_list:
                article_dict = article.to_dict()
                article_id = str(article_dict.get('_id'))  # 確保 ID 是字符串形式
                if article_id in article_topics:
                    article_dict['topics'] = article_topics[article_id]
                else:
                    article_dict['topics'] = []
                news_with_topics.append(article_dict)

            # Save the combined data
            output_path = PathManager.get_news_with_topics_path(self.region, self.date)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(news_with_topics, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Saved {len(news_with_topics)} news articles with topics to {output_path}")

        except Exception as e:
            self.logger.error(f"Error saving news with topics: {str(e)}")