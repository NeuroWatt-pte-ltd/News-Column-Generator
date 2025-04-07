from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

@dataclass
class NewsArticle:
    """Data model for news articles, used to unify the structure of news data"""
    
    # Basic attributes
    id: Optional[str] = None
    title: str = ""
    summary: str = ""
    url: str = ""
    source: str = ""
    category: str = ""
    published_at: Optional[datetime] = None
    
    # Analysis results
    topics: List[Dict[str, Any]] = field(default_factory=list)  # List [{"topic_id": id, "probability": prob}, ...]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsArticle':
        """Create a news article object from a dictionary
        
        :param data: Dictionary containing news article data
        :return: NewsArticle instance
        """
        # Handle ID
        article_id = None
        if '_id' in data:
            if isinstance(data['_id'], dict) and '$oid' in data['_id']:
                article_id = data['_id']['$oid']
            elif isinstance(data['_id'], str) or isinstance(data['_id'], int):
                article_id = str(data['_id'])
        
        # Handle datetime
        published_at = None
        if 'publishedAt' in data:
            published_at = cls._parse_datetime(data['publishedAt'])
        elif 'published_at' in data:
            published_at = cls._parse_datetime(data['published_at'])
        
        # Create object
        article = cls(
            id=article_id,
            title=data.get('title', ''),
            summary=data.get('summary', ''),
            url=data.get('url', ''),
            source=data.get('source', ''),
            category=data.get('category', ''),
            published_at=published_at,
            topics=data.get('topics', [])
        )
        
        return article
    
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
        
        :return: Dictionary representation of the news article
        """
        # Create basic dictionary
        result = {
            'title': self.title,
            'summary': self.summary,
            'url': self.url,
            'source': self.source,
            'category': self.category,
            'topics': self.topics
        }
        
        # Add ID (if available)
        if self.id:
            result['_id'] = self.id
        
        # Add datetime (if available)
        if self.published_at:
            if isinstance(self.published_at, datetime):
                result['published_at'] = self.published_at.isoformat()
            else:
                result['published_at'] = self.published_at
        
        return result
    
    def get_main_topic(self) -> Optional[int]:
        """Get the main topic ID (if available)
        
        :return: Main topic ID or None if no topics
        """
        if self.topics and len(self.topics) > 0:
            return self.topics[0].get('topic_id')
        return None
    
