import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logging import setup_logger
from utils.path_manager import PathManager


class FileManager:
    """File manager responsible for reading and writing files"""
    
    def __init__(self):
        """Initialize the file manager"""
        self.logger = setup_logger("File Manager")
    
    def read_news_file(self, region: str, date: str, custom_path: Optional[str] = None) -> List[Dict]:
        """
        Read news file
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :param custom_path: Custom file path (optional)
        :return: List of news articles
        """
        try:
            # Use custom path if provided
            if custom_path:
                file_path = Path(custom_path)
            else:
                # Use PathManager to get path
                file_path = PathManager.get_news_input_path(region, date)
            
            self.logger.info(f"Reading news from {file_path}")
            
            if not file_path.exists():
                self.logger.warning(f"News file not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            
            self.logger.info(f"Read {len(news_data)} news items from {file_path}")
            return news_data
            
        except Exception as e:
            self.logger.error(f"Error reading news file: {str(e)}")
            return []
    
    def save_topics(self, topics_data: Dict, region: str, date: str) -> bool:
        """
        Save topic data
        
        :param topics_data: Topic data dictionary
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Whether save was successful
        """
        try:
            # Use PathManager to get path
            file_path = PathManager.get_topics_path(region, date)
            # Ensure directory exists
            PathManager.ensure_dir(file_path.parent)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(topics_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved topics data to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving topics data: {str(e)}")
            return False
    
    def save_reports(self, reports: List[Dict], region: str, date: str) -> bool:
        """
        Save generated reports
        
        :param reports: List of reports
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Whether save was successful
        """
        try:
            # Use PathManager to get path
            file_path = PathManager.get_reports_path(region, date)
            # Ensure directory exists
            PathManager.ensure_dir(file_path.parent)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved {len(reports)} reports to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving reports: {str(e)}")
            return False
    
    def read_topics(self, region: str, date: str) -> Dict:
        """
        Read topic data
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Topic data dictionary
        """
        try:
            # Use PathManager to get path
            file_path = PathManager.get_topics_path(region, date)
            
            if not file_path.exists():
                self.logger.warning(f"Topics file not found: {file_path}")
                return {"topics": []}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                topics_data = json.load(f)
            
            self.logger.info(f"Read topics data from {file_path}")
            return topics_data
            
        except Exception as e:
            self.logger.error(f"Error reading topics data: {str(e)}")
            return {"topics": []}
    
    def read_reports(self, region: str, date: str) -> List[Dict]:
        """
        Read generated reports
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: List of reports
        """
        try:
            # Use PathManager to get path
            file_path = PathManager.get_reports_path(region, date)
            
            if not file_path.exists():
                self.logger.warning(f"Reports file not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reports = json.load(f)
            
            self.logger.info(f"Read {len(reports)} reports from {file_path}")
            return reports
            
        except Exception as e:
            self.logger.error(f"Error reading reports: {str(e)}")
            return []
