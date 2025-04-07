import json
from datetime import datetime
import pytz
from typing import Dict, List, Any

from utils import setup_logger


class ReportFormatter:
    """Handle report formatting and compilation functions"""
    
    def __init__(self, region: str):
        """
        Initialize formatter
        
        :param region: Region code (tw/us/vt)
        """
        self.region = region
        self.logger = setup_logger(f"ReportFormatter-{region}")
        
        # Reference news title
        self.reference_news_title = 'Reference News'
        if region == 'tw':
            self.reference_news_title = '參考新聞'
        elif region == 'vt':
            self.reference_news_title = 'Tin tức tham khảo'
    
    def append_reference_news(self, content: str, filtered_news: List[Dict]) -> str:
        """
        Append reference news list to content
        
        :param content: Report content
        :param filtered_news: Filtered news list
        :return: Content with appended reference news
        """
        # Add reference news title
        result = f"{content}\n\n### {self.reference_news_title}\n\n"
        
        # Add all news
        for i, news in enumerate(filtered_news, 1):
            news_title = news.get('title', '')
            result += f"{i}. [{news_title}]({news.get('url', '')})\n"
        
        return result
    
    def compile_report(
        self,
        topic: Dict,
        report_content: Dict[str, str],
        filtered_news: List[Dict],
        sentiment_analysis: Dict[str, List[str]],
        source_lang: str,
    ) -> Dict[str, Any]:
        """
        Compile final report
        
        :param topic: Topic data
        :param report_content: Main report content {'title': 'title', 'content': 'content'}
        :param filtered_news: Filtered news list
        :param sentiment_analysis: Stock sentiment analysis results
        :param source_lang: Source language code
        :return: Complete report data
        """
        try:
            # Add reference news to main content
            main_content = self.append_reference_news(
                report_content['content'],
                filtered_news
            )
            
            # Build basic report
            report = {
                'topic_id': topic['topic_id'],
                'topic_content': topic['content'],
                'title': report_content['title'],
                'content': main_content,
                'published_at': datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                'reference_news': [
                    {
                        'title': news.get('title', ''),
                        'url': news.get('url', ''),
                        'source': news.get('source', '')
                    } 
                    for news in filtered_news
                ]
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error compiling report: {str(e)}")
            raise
    
    def format_report_for_display(self, report: Dict) -> Dict[str, str]:
        """
        Format report for display
        
        :param report: Report data
        :return: Formatted report {'title': 'title', 'content': 'content'}
        """
        try:
            # Get title and content
            title = report.get('title', '')
            content = report.get('content', '')
            
            return {
                'title': title,
                'content': content
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting report for display: {str(e)}")
            return {'title': '', 'content': ''}