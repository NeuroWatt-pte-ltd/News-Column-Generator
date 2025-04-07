import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.logging import setup_logger


class ConfigLoader:
    """Configuration loader providing unified configuration reading functionality"""
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration loader"""
        # Skip if already initialized
        if getattr(self, "_initialized", False):
            return
            
        self.logger = setup_logger("Config Loader")
        self.logger.info("Initializing ConfigLoader")
        
        # Configuration file paths
        self.config_dir = Path("configs")
        self.config_file = self.config_dir / "config.yaml"
        self.prompts_dir = self.config_dir / "prompts"
        
        # Configuration cache
        self._config = None
        self._prompts = {}
        
        # Mark as initialized
        self._initialized = True
    
    def get_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        Get main configuration
        
        :param reload: Whether to reload the configuration file, defaults to False
        :return: Configuration dictionary
        """
        if self._config is None or reload:
            try:
                if not self.config_file.exists():
                    self.logger.error(f"Config file not found: {self.config_file}")
                    return {}
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
                self.logger.info("Loaded main configuration")
            except Exception as e:
                self.logger.error(f"Error loading config: {str(e)}")
                self._config = {}
        
        return self._config
    
    def get_supported_regions(self) -> List[str]:
        """
        Get list of supported region codes
        
        :return: List of all supported region codes
        """
        config = self.get_config()
        return list(config.get('regions', {}).keys())
    
    def get_region_info(self, region: str) -> Dict[str, Any]:
        """
        Get configuration information for a specific region
        
        :param region: Region code
        :return: Region configuration information
        """
        config = self.get_config()
        return config.get('regions', {}).get(region, {})
    
    def get_region_language(self, region: str) -> str:
        """
        Get the primary language for a region
        
        :param region: Region code
        :return: Language code
        """
        region_info = self.get_region_info(region)
        return region_info.get('main_language', 'eng')
    
    def get_region_timezone(self, region: str) -> str:
        """
        Get the timezone for a region
        
        :param region: Region code
        :return: Timezone name
        """
        region_info = self.get_region_info(region)
        return region_info.get('timezone', 'UTC')
    
    def get_region_weighted_sources(self, region: str) -> Dict[str, float]:
        """
        Get weighted news sources for a region
        
        :param region: Region code
        :return: Source weight dictionary {source: weight}
        """
        region_info = self.get_region_info(region)
        return region_info.get('weighted_sources', {})
    
    def get_region_stopwords(self, region: str) -> List[str]:
        """
        Get stopwords for a region
        
        :param region: Region code
        :return: List of stopwords
        """
        region_info = self.get_region_info(region)
        return region_info.get('stopwords', [])
    
    def get_region_input_file(self, region: str, date: str) -> str:
        """
        Get input file template for a region
        
        :param region: Region code
        :param date: Date string
        :return: Input file path
        """
        region_info = self.get_region_info(region)
        template = region_info.get('input_file', f"data/{region}_news_{{date}}.json")
        return template.format(date=date)
    
    def get_prompt(self, category: str, prompt_name: str, **kwargs) -> str:
        """
        Get prompt template
        
        :param category: Prompt category (e.g., report_generation)
        :param prompt_name: Prompt name (e.g., system or user)
        :param kwargs: Variable values for the prompt
        :return: Formatted prompt
        """
        try:
            # Look for prompt template in cache
            if category not in self._prompts:
                prompt_file = self.prompts_dir / f"{category}.yaml"
                if not prompt_file.exists():
                    self.logger.error(f"Prompt file not found: {prompt_file}")
                    return ""
                
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    self._prompts[category] = yaml.safe_load(f)
            
            # Get prompt template
            prompt_template = self._prompts[category].get(prompt_name, "")
            if not prompt_template:
                self.logger.warning(f"Prompt '{prompt_name}' not found in category '{category}'")
                return ""
            
            # Format prompt
            return prompt_template.format(**kwargs)
            
        except Exception as e:
            self.logger.error(f"Error getting prompt: {str(e)}")
            return ""
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM service configuration
        
        :return: LLM configuration dictionary
        """
        config = self.get_config()
        return config.get('llm', {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """
        Get system configuration
        
        :return: System configuration dictionary
        """
        config = self.get_config()
        return config.get('system', {})
    
    def get_topic_analysis_config(self) -> Dict[str, Any]:
        """
        Get topic analysis configuration
        
        :return: Topic analysis configuration dictionary
        """
        config = self.get_config()
        return config.get('topic_analysis', {})
    
    def get_report_config(self) -> Dict[str, Any]:
        """
        Get report configuration
        
        :return: Report configuration dictionary
        """
        config = self.get_config()
        return config.get('report', {})


def get_config_loader() -> ConfigLoader:
    """
    Get configuration loader instance
    
    :return: ConfigLoader instance
    """
    return ConfigLoader()
