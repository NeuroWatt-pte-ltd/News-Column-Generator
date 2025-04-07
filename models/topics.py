from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Topic:
    """Data model for topics, representing topics extracted from articles"""
    
    topic_id: int
    content: str
    count: int = 0
    weighted_count: float = 0.0
    keywords: List[str] = field(default_factory=list)
    article_ids: List[str] = field(default_factory=list)
    
    # Selection reason (if this is a selected topic)
    selection_reason: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Topic':
        """Create a topic object from a dictionary
        
        :param data: Dictionary containing topic data
        :return: Topic instance
        """
        return cls(
            topic_id=int(data['topic_id']),
            content=data['content'],
            count=data.get('count', 0),
            weighted_count=data.get('weighted_count', 0.0),
            keywords=data.get('keywords', []),
            article_ids=data.get('article_ids', []),
            selection_reason=data.get('selection_reason', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation
        
        :return: Dictionary representation of the topic
        """
        result = {
            'topic_id': self.topic_id,
            'content': self.content,
            'count': self.count,
            'weighted_count': self.weighted_count
        }
        
        if self.keywords:
            result['keywords'] = self.keywords
            
        if self.article_ids:
            result['article_ids'] = self.article_ids
            
        if self.selection_reason:
            result['selection_reason'] = self.selection_reason
            
        return result
    
    
@dataclass
class TopicStats:
    """Data model for topic and keyword statistics"""
    
    topics: List[Topic] = field(default_factory=list)
    keywords: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicStats':
        """Create a topic statistics object from a dictionary
        
        :param data: Dictionary containing topic statistics data
        :return: TopicStats instance
        """
        topics = [Topic.from_dict(topic_data) for topic_data in data.get('topics', [])]
        
        return cls(
            topics=topics,
            keywords=data.get('keywords', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation
        
        :return: Dictionary representation of the topic statistics
        """
        return {
            'topics': [topic.to_dict() for topic in self.topics],
            'keywords': self.keywords
        }
    
    def sort_topics_by_weighted_count(self) -> List[Topic]:
        """Sort topics by weighted count
        
        :return: Sorted list of topics
        """
        return sorted(self.topics, key=lambda t: t.weighted_count, reverse=True)
    
    def get_topic_by_id(self, topic_id: int) -> Optional[Topic]:
        """Find topic by ID
        
        :param topic_id: The topic ID to search for
        :return: Topic instance if found, None otherwise
        """
        for topic in self.topics:
            if topic.topic_id == topic_id:
                return topic
        return None
    
    