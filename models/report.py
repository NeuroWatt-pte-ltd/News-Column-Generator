from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

@dataclass
class Report:
    """Data model for reports, representing column reports generated from topics and related news"""
    
    # Basic information
    topic_id: int
    topic_content: str
    published_at: Optional[datetime] = None
    
    # Content
    title: str = ""
    content: str = ""
    
    # Reference materials
    reference_news: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Report':
        """Create a report object from a dictionary
        
        :param data: Dictionary containing report data
        :return: Report instance
        """
        # Handle datetime
        published_at = None
        if 'published_at' in data:
            published_at = cls._parse_datetime(data['published_at'])
        elif 'publishedAt' in data:
            published_at = cls._parse_datetime(data['publishedAt'])
        
        return cls(
            topic_id=int(data['topic_id']),
            topic_content=data['topic_content'],
            published_at=published_at,
            title=data.get('title', ''),
            content=data.get('content', ''),
            reference_news=data.get('reference_news', [])
        )
    
    @staticmethod
    def _parse_datetime(dt_value):
        """Parse datetime value
        
        :param dt_value: Datetime value in various formats
        :return: Parsed datetime object or original value if parsing fails
        """
        if isinstance(dt_value, str):
            try:
                if 'T' in dt_value:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                else:
                    return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S %Z')
                except ValueError:
                    return dt_value
        return dt_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation
        
        :return: Dictionary representation of the report
        """
        result = {
            'topic_id': self.topic_id,
            'topic_content': self.topic_content,
            'title': self.title,
            'content': self.content,
            'reference_news': self.reference_news
        }
        
        # Add published time
        if self.published_at:
            if isinstance(self.published_at, datetime):
                result['published_at'] = self.published_at.isoformat()
            else:
                result['published_at'] = self.published_at
        
        return result
    
    def save_to_file(self, file_path: str) -> None:
        """Save report to a file
        
        :param file_path: Path to save the file
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Report':
        """Load report from a file
        
        :param file_path: Path to the file
        :return: Report instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    