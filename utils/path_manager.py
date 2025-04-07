from pathlib import Path
import os


class PathManager:
    """
    Path Manager
    
    Centrally manages all file path logic in the system, providing static methods
    to obtain paths for various data files.
    """
    
    @staticmethod
    def ensure_dir(path: Path) -> Path:
        """
        Ensure directory exists and return the path
        
        :param path: Directory path to ensure
        :return: The ensured path
        """
        os.makedirs(path, exist_ok=True)
        return path
    
    @staticmethod
    def get_output_base(region: str, date: str) -> Path:
        """
        Get base output path
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Base output path (data/output/{date}/{region})
        """
        return Path(f"data/output/{date}/{region}")
    
    @staticmethod
    def get_news_input_path(region: str, date: str) -> Path:
        """
        Get news input file path
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: News input file path (data/{region}_news_{date}.json)
        """
        return Path(f"data/{region}_news_{date}.json")
    
    @staticmethod
    def get_topics_path(region: str, date: str) -> Path:
        """
        Get topics file path
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Topics file path (data/output/{date}/{region}/topics_{date}.json)
        """
        base = PathManager.get_output_base(region, date)
        return base / f"topics_{date}.json"
    
    @staticmethod
    def get_reports_path(region: str, date: str) -> Path:
        """
        Get reports file path
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Reports file path (data/output/{date}/{region}/reports_{date}.json)
        """
        base = PathManager.get_output_base(region, date)
        return base / f"reports_{date}.json"
    
    @staticmethod
    def get_execution_summary_path(region: str, date: str) -> Path:
        """
        Get execution summary file path
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: Execution summary file path (data/output/{date}/{region}/execution_summary_{date}.json)
        """
        base = PathManager.get_output_base(region, date)
        return base / f"execution_summary_{date}.json"

    @staticmethod
    def get_news_with_topics_path(region: str, date: str) -> Path:
        """
        Get path for news file with topics
        
        :param region: Region code
        :param date: Date string (YYYYMMDD)
        :return: News with topics file path
        """
        base = PathManager.get_output_base(region, date)
        return base / f"news_with_topics_{date}.json"
