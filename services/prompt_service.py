import yaml
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path
from utils import setup_logger


class PromptCategory(str, Enum):
    """Enumeration of various prompt categories."""
    TOPIC_SELECTION = "topic_selection"
    NEWS_FILTERING = "news_filtering"
    REPORT_GENERATION = "report_generation"
    VALIDATION = "validation"


class PromptService:
    """Central management service for all system prompts."""

    # Singleton instance and initialization status
    _instance = None
    _is_initialized = False

    def __new__(cls, *args, **kwargs):
        """
        Ensure class follows singleton pattern
        
        :return: Singleton instance of PromptService
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, prompt_templates_path: Optional[str] = None):
        """
        Initialize the prompt service
        
        :param prompt_templates_path: Path to prompt templates directory
        """
        # Skip if already initialized
        if self._is_initialized:
            return

        # Set up logger
        self.logger = setup_logger("Prompt Service")
        self.logger.debug("Initializing PromptService...")

        # Set prompt templates path
        if prompt_templates_path is None:
            prompt_templates_path = "configs/prompts"

        self.templates_path = Path(prompt_templates_path)
        self.prompts = {}

        try:
            # Check if templates directory exists
            if not self.templates_path.exists():
                raise FileNotFoundError(f"Prompt templates directory not found: {self.templates_path}")

            # Load all prompt templates
            self._load_prompt_templates()

            # Mark initialization as complete
            self._is_initialized = True
            self.logger.info(f"Successfully loaded prompt templates from {self.templates_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize PromptService: {str(e)}")
            raise

    def _load_prompt_templates(self):
        """Load all prompt template files"""
        template_files = list(self.templates_path.glob("*.yaml"))
        
        if not template_files:
            self.logger.warning(f"No prompt template files found in {self.templates_path}")
            return

        for template_file in template_files:
            try:
                category = template_file.stem  # Use filename as category name
                
                with open(template_file, 'r', encoding="utf-8") as f:
                    template_data = yaml.safe_load(f)
                    # Use file contents directly, no additional structure needed
                    self.prompts[category] = template_data
                
                self.logger.debug(f"Loaded prompt template: {template_file}")
            except Exception as e:
                self.logger.error(f"Error loading template {template_file}: {str(e)}")

    def get_prompt(self, category, prompt_name: str, **kwargs) -> str:
        """
        Get and format a prompt template
        
        :param category: Prompt category (can be PromptCategory enum or string)
        :param prompt_name: Name of the prompt
        :param kwargs: Formatting parameters
        :return: Formatted prompt string
        """
        try:
            # Handle category
            if isinstance(category, PromptCategory):
                category_value = category.value
            else:
                category_value = str(category)
                
            self.logger.debug(f"Getting prompt - category: {category_value}, name: {prompt_name}")

            # Get prompt dictionary for category
            prompt_dict = self.prompts.get(category_value)
            if not prompt_dict:
                raise KeyError(f"Prompt category not found: {category_value}")
            
            # Get specific prompt by name
            prompt_template = prompt_dict.get(prompt_name)
            if not prompt_template:
                raise KeyError(f"Prompt name not found: {prompt_name} in category {category_value}")
            
            # Ensure retrieved value is a string
            if not isinstance(prompt_template, str):
                raise ValueError(f"Prompt '{prompt_name}' is not a string")
            
            # Format prompt with provided parameters
            result = prompt_template.format(**kwargs) if kwargs else prompt_template
            return result
        
        except KeyError as e:
            error_msg = f"Prompt not found: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        except Exception as e:
            self.logger.error(f"Error getting prompt: {str(e)}")
            raise

    def reload_templates(self) -> bool:
        """
        Reload all prompt templates
        
        :return: Whether reload was successful
        """
        try:
            self.prompts = {}
            self._load_prompt_templates()
            self.logger.info("Prompt templates reloaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error reloading prompt templates: {str(e)}")
            return False