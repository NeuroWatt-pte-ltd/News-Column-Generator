import asyncio
import click
from datetime import datetime
from typing import Optional, List
import sys
from pathlib import Path

from reporting import BaseReportGenerator
from runners import NewsReportBaseRunner
from utils import setup_logger, get_config_loader


logger = setup_logger("Main")


async def run_pipeline(
    regions: List[str],
    date: Optional[str] = None
) -> None:
    """
    Execute report generation pipeline
    
    :param regions: List of regions to process
    :param date: Specified date (YYYYMMDD)
    """
    try:
        logger.info(f"Starting report generation, date: {date or 'today'}, regions: {', '.join(regions)}")
        start_time = datetime.now()
        
        results = {}
        
        # Generate reports for each region
        for region in regions:
            logger.info(f"Processing region: {region}")
            try:
                # Use NewsReportBaseRunner to generate reports
                runner = NewsReportBaseRunner(
                    region=region,
                    date=date
                )
                
                # Execute report generation
                result = await runner.run()
                
                # Record results
                results[region] = {
                    "successful": True,
                    "global_reports_count": len(result.get("global_reports", [])),
                    "execution_time": result.get("execution_time", 0)
                }
                
                logger.info(f"Generated {len(result.get('global_reports', []))} global reports for {region}")
                
            except Exception as e:
                logger.error(f"Error generating reports for {region}: {str(e)}")
                results[region] = {
                    "successful": False,
                    "errors": [str(e)]
                }
        
        # Display execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Report generation pipeline completed, took {execution_time:.2f} seconds")
        
        # Display result summary
        success_count = sum(1 for r in results.values() if r.get("successful", False))
        failed_count = len(results) - success_count
        
        logger.info(f"Summary: {success_count} regions successful, {failed_count} regions failed")
        
        return results
                
    except Exception as e:
        logger.error(f"Error executing report generation pipeline: {str(e)}")
        raise


@click.command()
@click.option(
    '--mode',
    '-m',
    type=click.Choice(['once']),
    required=True,
    help='Execution mode: once (execute once)'
)
@click.option('--regions', '-r', multiple=True, required=True, help='Region codes (tw/us/vt)')
@click.option('--date', '-d', help='Specified date (YYYYMMDD)')
def main(
    mode: str,
    regions: tuple,
    date: Optional[str]
):
    """News Report Generation System"""
    try:
        # Validate date format
        if date:
            try:
                datetime.strptime(date, '%Y%m%d')
            except ValueError:
                logger.error("Invalid date format. Please use YYYYMMDD format")
                sys.exit(1)
        
        # Convert parameter format
        regions_list = list(regions)
        
        # Validate regions
        config_loader = get_config_loader()
        supported_regions = config_loader.get_supported_regions()
        for region in regions_list:
            if region not in supported_regions:
                logger.error(f"Unsupported region: {region}. Available regions: {', '.join(supported_regions)}")
                sys.exit(1)
        
        if mode == 'once':
            # Single execution mode
            logger.info(f"Starting single execution, regions: {', '.join(regions_list)}")
            
            asyncio.run(run_pipeline(
                regions=regions_list,
                date=date
            ))
            
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Program execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
