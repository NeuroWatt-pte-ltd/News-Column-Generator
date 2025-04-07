import json
import re
from typing import Dict, Any, Tuple, List, Union

from services import LLMService, PromptService, PromptCategory
from utils import setup_logger
from models import Report


class ReportValidator:
    """Handle report content validation functionality"""
    
    def __init__(self):
        """Initialize report validator"""
        self.logger = setup_logger("Report Validator")
        
        # Initialize services
        self.llm_service = LLMService(
            temperature=0,
            model_name="gpt-4o"
        )
        self.prompt_service = PromptService()
        
        # Set default word count limits
        self.default_min_words = 500
        self.default_max_words = 1500
    
    def validate_report_format(self, report_content: Dict[str, str]) -> bool:
        """
        Validate if the report format is correct
        
        :param report_content: Report content {'title': 'title', 'content': 'content'}
        :return: Whether the format is valid
        """
        if not isinstance(report_content, dict):
            self.logger.warning("Report content is not a dictionary")
            return False
            
        if 'title' not in report_content or 'content' not in report_content:
            self.logger.warning("Report content missing required fields (title or content)")
            return False
            
        if not report_content.get('title') or not report_content.get('content'):
            self.logger.warning("Report title or content is empty")
            return False
            
        return True
    
    def validate_word_count(self, content: str, min_words: int = 100, max_words: int = 2000) -> Tuple[bool, str, int]:
        """
        Validate if the content word count is within allowed range
        
        :param content: Content text
        :param min_words: Minimum word count
        :param max_words: Maximum word count
        :return: (is valid, reason, actual word count)
        """
        # Multilingual word counting
        word_count = self._count_words_multilingual(content)
        self.logger.debug(f"Calculated word count: {word_count}")
        
        if word_count < min_words:
            return False, f"Content too short ({word_count} words, minimum {min_words})", word_count
            
        if word_count > max_words:
            return False, f"Content too long ({word_count} words, maximum {max_words})", word_count
            
        return True, f"Content length acceptable ({word_count} words)", word_count
    
    def _count_words_multilingual(self, text: str) -> int:
        """
        Multilingual word counting, focusing on English, Vietnamese, and Chinese
        
        Processing method:
        - English and Vietnamese: These languages use spaces to separate words, count by words
        - Chinese: Count by characters, excluding punctuation and whitespace
        
        :param text: Text to count words for
        :return: Word count
        """
        if not text:
            return 0
            
        # Clean text
        text = text.strip()
        
        # Count Chinese characters (excluding punctuation and whitespace)
        chinese_char_count = sum(1 for char in text if self._is_chinese_char(char))
        
        # Count space-separated words (suitable for English and Vietnamese)
        space_separated_words = len(text.split())
        
        # Determine main language type
        # If Chinese characters make up more than 30%, consider it Chinese-dominated text
        if chinese_char_count > len(text) * 0.3:
            # Chinese-dominated text, count by characters
            self.logger.debug(f"Text appears to be Chinese dominant: {chinese_char_count} Chinese chars in {len(text)} total chars")
            # Add word count for non-Chinese parts (usually quoted English or Vietnamese)
            non_chinese_text = ''.join(' ' if self._is_chinese_char(char) or char.isspace() or self._is_punctuation(char) else char for char in text)
            non_chinese_words = len([word for word in non_chinese_text.split() if word])
            total_count = chinese_char_count + non_chinese_words
            self.logger.debug(f"Chinese char count: {chinese_char_count}, non-Chinese words: {non_chinese_words}, total: {total_count}")
            return total_count
        else:
            # English or Vietnamese-dominated text, count by space-separated words
            self.logger.debug(f"Text appears to be English or Vietnamese: {space_separated_words} words")
            return space_separated_words
    
    def _is_chinese_char(self, char: str) -> bool:
        """
        Determine if a character is a Chinese character
        
        :param char: Single character
        :return: Whether it's a Chinese character
        """
        # CJK Unified Ideographs range
        if '\u4e00' <= char <= '\u9fff':
            return True
        # CJK Unified Ideographs Extension A
        if '\u3400' <= char <= '\u4dbf':
            return True
        return False
    
    def _is_punctuation(self, char: str) -> bool:
        """
        Determine if a character is punctuation
        
        :param char: Single character
        :return: Whether it's punctuation
        """
        # Common Chinese and English punctuation
        punctuation_chars = '，。？！、；：""''（）【】《》〈〉『』「」﹁﹂…—－～·.,:;!?[](){}"\'+-*/=_'
        return char in punctuation_chars or char.isspace()
    
    def extract_title_content(self, text: str) -> Dict[str, str]:
        """
        Extract title and content from text
        
        :param text: Original text
        :return: {'title': 'title', 'content': 'content'}
        """
        try:
            # Try to parse as JSON format
            if text.strip().startswith('{') and text.strip().endswith('}'):
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and 'title' in data and 'content' in data:
                        return {
                            'title': data['title'],
                            'content': data['content']
                        }
                except json.JSONDecodeError:
                    pass
            
            # Try to extract title and content from text
            lines = text.strip().split('\n')
            
            # Find title
            title_line = None
            for i, line in enumerate(lines):
                if line.lower().startswith('title:'):
                    title_line = i
                    break
            
            # Find content
            content_line = None
            for i, line in enumerate(lines):
                if line.lower().startswith('content:'):
                    content_line = i
                    break
            
            # Extract title and content
            if title_line is not None and content_line is not None:
                title = lines[title_line].replace('Title:', '', 1).strip()
                content = '\n'.join(lines[content_line+1:]).strip()
                if not content and content_line > 0:
                    # Handle case where content might be on the same line
                    content = lines[content_line].replace('Content:', '', 1).strip()
                return {
                    'title': title,
                    'content': content
                }
            
            # If no standard format is found, try to extract based on line numbers
            if len(lines) > 1:
                title = lines[0].strip()
                content = '\n'.join(lines[1:]).strip()
                return {
                    'title': title,
                    'content': content
                }
            
            # If extraction fails, return empty result
            self.logger.warning("Failed to extract title and content from text")
            return {
                'title': '',
                'content': text
            }
                
        except Exception as e:
            self.logger.error(f"Error extracting title and content: {str(e)}")
            return {
                'title': '',
                'content': text
            }
    
    def _clean_json_response(self, response: str) -> str:
        """
        Clean JSON string from LLM response
        
        :param response: LLM response
        :return: Cleaned JSON string
        """
        # Remove Markdown code block markers
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, response)
        if match:
            return match.group(1).strip()
        
        # If no code block markers, return original response
        return response.strip()
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response
        
        :param response: LLM response
        :return: Parsed JSON dictionary
        """
        try:
            # Clean response
            cleaned_response = self._clean_json_response(response)
            
            # Parse JSON
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {response}")
            self.logger.error(f"JSON error: {str(e)}")
            raise
    
    async def validate_content(
        self, 
        content: str, 
        title: str, 
        min_words: int = None, 
        max_words: int = None
    ) -> Tuple[bool, str, int]:
        """
        Validate report content quality and basic format
        
        :param content: Report content
        :param title: Report title
        :param min_words: Minimum word count limit, if None uses default value
        :param max_words: Maximum word count limit, if None uses default value
        :return: (passes validation, reason, estimated word count)
        """
        self.logger.info(f"Validating content for title: {title}")
        
        # Perform format validation
        is_format_valid = self.validate_report_format({'title': title, 'content': content})
        if not is_format_valid:
            return False, "Invalid report format", 0
        
        # Perform word count validation
        min_words = min_words or self.default_min_words
        max_words = max_words or self.default_max_words
        basic_valid, reason, word_count = self.validate_word_count(
            content, min_words, max_words
        )
        
        if not basic_valid:
            self.logger.warning(f"Content word count validation failed: {reason}")
            return False, reason, word_count
            
        # Use LLM for content quality validation
        try:
            system_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.VALIDATION,
                prompt_name="system"
            )
            
            user_prompt = self.prompt_service.get_prompt(
                category=PromptCategory.VALIDATION,
                prompt_name="user",
                title=title,
                content=content
            )
            
            self.logger.debug(f"Sending content to LLM for quality validation")
            
            # Call LLM service
            response = await self.llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            self.logger.debug(f"LLM validation response: {response}")
            
            # Parse LLM response
            try:
                validation_result = self._parse_json_response(response)
                is_valid = validation_result.get('pass', False)
                reason = validation_result.get('reason', 'Unknown reason')
                issues = validation_result.get('issues', [])
                
                if not is_valid:
                    issue_details = "; ".join(issues) if issues else ""
                    detailed_reason = f"{reason} {issue_details}".strip()
                    self.logger.warning(f"Content quality validation failed: {detailed_reason}")
                    return False, detailed_reason, word_count
                else:
                    self.logger.info(f"Content quality validation passed: {reason}")
                
                # Return basic validation word count result
                return True, reason, word_count
                
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse content validation response: {response}")
                # If parsing fails, use basic validation result
                return basic_valid, f"{reason} (LLM validation response parsing failed)", word_count
                
        except Exception as e:
            self.logger.error(f"Error in LLM content validation: {str(e)}")
            # If LLM validation fails, use basic validation result
            return basic_valid, f"{reason} (LLM validation failed: {str(e)})", word_count
    
    async def validate_report_completeness(self, report: Union[Dict[str, Any], Report]) -> Tuple[bool, List[str]]:
        """
        Validate final report completeness
        
        :param report: Complete report (Report object or dictionary), including all fields
        :return: (is complete, list of missing or problematic fields)
        """
        self.logger.info("Validating report completeness")
        
        missing_fields = []
        
        # Check required fields
        required_fields = [
            'topic_id',
            'topic_content',
            'title',
            'content',
            'published_at'
        ]
        
        # Convert Report object to dictionary for checking
        if isinstance(report, Report):
            report_dict = report.to_dict()
        else:
            report_dict = report
        
        # Check basic required fields
        for field in required_fields:
            if field not in report_dict or report_dict[field] is None or report_dict[field] == '':
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
