from abc import ABC
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz
from pathlib import Path
import json
import asyncio
import time
import traceback

from reporting import BaseReportGenerator
from utils import setup_logger, get_config_loader, PathManager


class NewsReportBaseRunner:
    """Base runner for news report generation"""
    
    def __init__(self, region: str, date: Optional[str] = None):
        """
        Initialize the runner
        
        :param region: Region code (tw/us/vt)
        :param date: Specified date in YYYYMMDD format. If not specified, current date will be used
        """
        self.region = region
        self.date = date or datetime.now().strftime('%Y%m%d')
        self.logger = setup_logger(f"NewsReportRunner-{region}")
        
        # Use ConfigLoader to load configuration
        self.config_loader = get_config_loader()
        
        # Get region configuration
        self.region_config = self.config_loader.get_region_info(region)
        if not self.region_config:
            raise ValueError(f"No configuration found for region: {region}")
        
        # Set timezone
        self.timezone = self.region_config.get('timezone', 'UTC')
        self.logger.info(f"Using timezone: {self.timezone}")
        
        # Use PathManager to set output path
        self.output_path = PathManager.get_output_base(region, self.date)
        PathManager.ensure_dir(self.output_path)
    
    def get_categories(self) -> List[str]:
        """Get category list from configuration file"""
        categories_config = self.config_loader.get_categories_config()
        return [cat["code"] for cat in categories_config.get("categories", [])]
    
    async def generate_global_reports(self) -> List[Dict]:
        """Generate global reports"""
        self.logger.info(f"Generating global reports for {self.region} on {self.date}")
        
        try:
            # Generate new reports
            generator = BaseReportGenerator(
                date=self.date,
                region=self.region
            )
            
            reports = await generator.execute()
            
            # Log generated report information for debugging
            if reports:
                for i, report in enumerate(reports):
                    self.logger.debug(f"Report {i+1} summary - topic_id: {getattr(report, 'topic_id', 'MISSING')}")
                    self.logger.debug(f"Report {i+1} has title: {bool(report.title) if hasattr(report, 'title') else False}")
                    self.logger.debug(f"Report {i+1} has content: {bool(report.content) if hasattr(report, 'content') else False}")
                
                self.logger.info(f"Successfully generated {len(reports)} global reports")
            else:
                self.logger.warning("No global reports were generated")
                
            return reports
            
        except Exception as e:
            self.logger.error(f"Error generating global reports: {str(e)}")
            traceback.print_exc()
            raise
    
    async def run(self) -> Dict[str, Any]:
        """
        Execute news report generation process
        
        :return: Execution results
        """
        start_time = time.time()
        try:
            # Generate global reports
            global_reports = await self.generate_global_reports()
            self.logger.info(f"Successfully generated {len(global_reports)} global reports")
            
            # Save global reports
            if global_reports:
                # Convert Report objects to dictionaries
                global_reports_dicts = [report.to_dict() for report in global_reports]
                
                global_reports_path = PathManager.get_reports_path(self.region, self.date)
                with open(global_reports_path, 'w', encoding='utf-8') as f:
                    json.dump(global_reports_dicts, f, ensure_ascii=False, indent=2)
                self.logger.info(f"Saved {len(global_reports)} global reports to {global_reports_path}")
            
            # Save execution summary
            try:
                summary = {
                    "execution_time": datetime.now().isoformat(),
                    "region": self.region,
                    "date": self.date,
                    "global_reports_count": len(global_reports)
                }
                
                summary_path = PathManager.get_execution_summary_path(self.region, self.date)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                    
                self.logger.info(f"Execution summary saved to {summary_path}")
            except Exception as summary_err:
                self.logger.error(f"Error saving execution summary: {str(summary_err)}")
                traceback.print_exc()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                "global_reports": [report.to_dict() for report in global_reports],  # Also convert to dictionaries in the return result
                "execution_time": execution_time
            }
        except Exception as e:
            self.logger.error(f"Error generating reports: {str(e)}")
            traceback.print_exc()
            return {
                "global_reports": [],
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
