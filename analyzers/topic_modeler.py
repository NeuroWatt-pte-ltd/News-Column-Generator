# Standard library imports
import os
import re
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Union

# Third-party library imports
import jieba
import numpy as np
from gensim import corpora, models
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.tokenize import word_tokenize
import pyvi
from pyvi import ViTokenizer

# Local application imports
from utils import setup_logger, get_config_loader
from models import NewsArticle


class TopicModeler:
    """Topic modeling tool, responsible for text processing and topic modeling"""
    
    def __init__(self, region: str):
        """
        Initialize topic modeler
        
        :param region: Region code
        """
        self.region = region
        self.logger = setup_logger("Topic Modeler")

        # Load configuration
        self.config_loader = get_config_loader()
        self.region_info = self.config_loader.get_region_info(region)
        
        # Set stopwords and weights
        self.stopwords = set(self.region_info.get('stopwords', []))
        self.weighted_sources = self.region_info.get('weighted_sources', {})
        self.main_language = self.region_info.get('main_language', 'eng')
        
        # Set weight counters
        self.keyword_counter = Counter()
        self.weighted_keyword_counter = Counter()
        self.topic_counter = Counter()
        self.weighted_topic_counter = Counter() 
        
        # Set jieba cache directory (only needed when processing Chinese)
        if self.region == 'tw':
            jieba_cache_dir = Path("data/temp/jieba_cache")
            jieba_cache_dir.mkdir(parents=True, exist_ok=True)
            jieba.dt.tmp_dir = str(jieba_cache_dir)
            
            # If there's a custom dictionary, load it
            custom_dict_path = self.region_info.get('jieba_dict_path')
            if custom_dict_path and os.path.exists(custom_dict_path):
                jieba.load_userdict(custom_dict_path)
                self.logger.info(f"Loaded custom dictionary for jieba: {custom_dict_path}")
        
        # Download NLTK data for English tokenization
        if self.region == 'us':
            try:
                nltk.download('punkt', quiet=True)
                self.logger.info("NLTK punkt tokenizer downloaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to download NLTK data: {str(e)}")
                
        self.logger.info(f"Initialized TopicModeler for region: {region}")
    
    def preprocess(self, text: str) -> List[str]:
        """
        Preprocess text according to region
        
        :param text: Original text
        :return: List of processed tokens
        """
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip().lower()
        
        # Tokenize according to region
        if self.region == 'tw':
            # Chinese tokenization
            tokens = jieba.cut(text)
        elif self.region == 'vt':
            # Vietnamese tokenization
            try:
                text = ViTokenizer.tokenize(text)
                tokens = text.split()
            except Exception as e:
                self.logger.error(f"Error in Vietnamese tokenization: {str(e)}")
                tokens = text.split()
        elif self.region == 'us':
            # English tokenization
            try:
                tokens = word_tokenize(text)
            except Exception as e:
                self.logger.error(f"Error in English tokenization: {str(e)}")
                tokens = text.split()
        else:
            # Other regions tokenize by space
            tokens = text.split()
            
        # Filter stopwords
        processed_tokens = [
            token for token in tokens 
            if token not in self.stopwords 
            and len(token) > 1 
            and not token.isspace()
            and not token.isdigit()
        ]
        
        return processed_tokens
    
    async def perform_topic_modeling(self, news_list: List[Union[Dict, NewsArticle]]) -> Dict[str, Any]:
        """
        Perform topic modeling
        
        :param news_list: News list (can be NewsArticle objects or dictionaries)
        :return: Topic data {"topics": [...]}
        """
        try:
            self.logger.info(f"Starting topic modeling for {len(news_list)} news articles")
            
            # Extract text and keep track of article IDs
            documents = []
            article_ids = []
            for news in news_list:
                # Handle different types of input
                if isinstance(news, NewsArticle):
                    article_id = news.id
                    summary = news.summary or ""
                    if not summary:
                        title = news.title or ""
                        content = news.content[:500] if news.content else ""
                        summary = f"{title} {content}"
                else:
                    article_id = news.get("_id")
                    summary = news.get("summary", "")
                    if not summary:
                        title = news.get("title", "")
                        content = news.get("content", "")[:500]
                        summary = f"{title} {content}"
                
                documents.append(summary)
                article_ids.append(article_id)
            
            # Preprocess documents
            processed_docs = [self.preprocess(doc) for doc in documents]
            processed_docs = [doc for doc in processed_docs if doc]
            
            if not processed_docs:
                self.logger.warning("No valid documents after preprocessing")
                return {"topics": []}
            
            self.logger.info(f"Preprocessed {len(processed_docs)} valid documents")
            
            # Build dictionary and corpus
            dictionary = corpora.Dictionary(processed_docs)
            dictionary.filter_extremes(no_below=2, no_above=0.9)
            corpus = [dictionary.doc2bow(doc) for doc in processed_docs]
            
            # Set number of topics
            topic_config = self.config_loader.get_topic_analysis_config()
            num_topics = self._adjust_num_topics(
                len(news_list), 
                min_topics=topic_config.get('min_topics', 5),
                max_topics=topic_config.get('max_topics', 20)
            )
            
            self.logger.info(f"Training LDA model with {num_topics} topics")
            
            # Set LDA model parameters
            model_params = {
                'corpus': corpus,
                'id2word': dictionary,
                'num_topics': num_topics,
                'passes': 15,
                'alpha': 'symmetric',
                'eta': 'symmetric',
                'random_state': 42,
                'minimum_probability': 0.01
            }
            
            if self.region == 'vt':
                model_params.update({
                    'iterations': 100,
                    'passes': 20,
                    'minimum_probability': 0.05,
                    'decay': 0.5
                })
            
            # Create LDA model
            lda_model = models.LdaModel(**model_params)
            
            # Calculate topic distribution and weights
            self._update_topic_counts(news_list, dictionary, lda_model)
            
            # Generate topic list with article assignments
            topics = []
            article_topic_mapping = {}  # 用於追蹤每篇文章的主題分配
            
            for topic_id in range(num_topics):
                try:
                    # Get topic terms
                    topic_terms = lda_model.get_topic_terms(topic_id, topn=5)
                    keywords = [dictionary[term_id] for term_id, _ in topic_terms]
                    
                    # Get articles for this topic
                    topic_articles = []
                    
                    # Process each document's topic distribution
                    for idx, doc_topics in enumerate(lda_model[corpus]):
                        article_id = article_ids[idx]
                        for t_id, prob in doc_topics:
                            if t_id == topic_id and prob >= 0.3:  # 主題機率閾值
                                topic_articles.append(article_id)
                                # 將主題資訊加入文章的映射中
                                if article_id not in article_topic_mapping:
                                    article_topic_mapping[article_id] = []
                                article_topic_mapping[article_id].append({
                                    'topic_id': topic_id,
                                    'probability': float(prob),
                                    'keywords': keywords
                                })
                    
                    # Create topic entry
                    content = " + ".join(f'"{keyword}"' for keyword in keywords)
                    count = self.topic_counter.get(topic_id, 0)
                    weighted_count = round(self.weighted_topic_counter.get(topic_id, 0), 2)
                    
                    topics.append({
                        "topic_id": topic_id,
                        "content": content,
                        "count": count,
                        "weighted_count": weighted_count,
                        "keywords": keywords,
                        "article_ids": topic_articles
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing topic {topic_id}: {str(e)}")
                    continue
            
            # Sort topics by weighted count
            topics = sorted(topics, key=lambda x: x['weighted_count'], reverse=True)
            
            # Update news articles with their topics
            for news in news_list:
                article_id = news.id if isinstance(news, NewsArticle) else news.get("_id")
                if article_id in article_topic_mapping:
                    if isinstance(news, NewsArticle):
                        news.topics = article_topic_mapping[article_id]
                    else:
                        news["topics"] = article_topic_mapping[article_id]
            
            self.logger.info(f"Topic modeling completed, found {len(topics)} topics")
            return {"topics": topics}
            
        except Exception as e:
            self.logger.error(f"Error in topic modeling: {str(e)}")
            return {"topics": []}
    
    def _update_topic_counts(self, news_list: List[Union[Dict, NewsArticle]], dictionary, lda_model):
        """
        Update topic and keyword counts
        
        :param news_list: News list (can be NewsArticle objects or dictionaries)
        :param dictionary: Dictionary
        :param lda_model: LDA model
        """
        # Reset counters
        self.topic_counter.clear()
        self.weighted_topic_counter.clear()
        self.keyword_counter.clear()
        self.weighted_keyword_counter.clear()
        
        for article in news_list:
            # Handle different types of input
            if isinstance(article, NewsArticle):
                # Handle NewsArticle object
                summary = article.summary or ""
                if not summary:
                    title = article.title or ""
                    content = article.content[:500] if article.content else ""  # Limit content length
                    summary = f"{title} {content}"
                source = article.source
            else:
                # Handle dictionary
                summary = article.get("summary", "")
                if not summary:
                    title = article.get("title", "")
                    content = article.get("content", "")[:500]  # Limit content length
                    summary = f"{title} {content}"
                source = article.get("source", "")
            
            # Process article to get topic allocation
            tokens = self.preprocess(summary)
            if not tokens:
                continue
                
            bow = dictionary.doc2bow(tokens)
            article_topics = lda_model.get_document_topics(bow)
            
            # Update topic counter
            weight = self.weighted_sources.get(source, 1.0)
            for topic_id, prob in article_topics:
                if prob >= 0.1:  # Only consider topics with probability greater than 0.1
                    self.topic_counter[topic_id] += 1
                    self.weighted_topic_counter[topic_id] += weight * prob
            
            # Update keyword counter
            for token in tokens:
                self.keyword_counter[token] += 1
                self.weighted_keyword_counter[token] += weight
    
    def _adjust_num_topics(self, article_count: int, min_topics: int = 5, max_topics: int = 20) -> int:
        """
        Dynamically adjust the number of topics based on article count
        
        :param article_count: Number of articles
        :param min_topics: Minimum number of topics
        :param max_topics: Maximum number of topics
        :return: Adjusted number of topics
        """
        if article_count <= 100:
            return min_topics
        elif article_count <= 500:
            # Linear growth
            return min(max_topics, min_topics + (article_count - 100) // 50)
        else:
            # Logarithmic growth
            log_growth = min_topics + int(math.log(article_count / 100, 2) * 3)
            return min(max_topics, log_growth)
