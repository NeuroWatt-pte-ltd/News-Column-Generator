# News Column Generator

A news analysis and column generation system that processes regional news, performs topic modeling, and generates high-quality editorial columns using LLM technology.

## Overview

News Column Generator is an automated system that:
1. Reads news articles from specific regions
2. Performs topic modeling to identify key themes
3. Selects the most important topics
4. Filters related news for each selected topic
5. Uses LLM to generate well-written columns based on the filtered news
6. Validates and formats the generated content

The system supports multiple regions (Taiwan, US, Vietnam) and their respective languages.

## Prerequisites

- Python 3.8+
- OpenAI API key
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```
git clone https://github.com/NeuroWatt-pte-ltd/News-Column-Generator.git
cd News-Column-Generator
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env_example` to `.env`
   - Add your OpenAI API key and set the desired log level:
```
OPENAI_API_KEY=your_openai_api_key_here
LOG_LEVEL=INFO
```

## Project Structure

- `analyzers/`: Contains modules for news filtering, topic modeling and content analysis
- `configs/`: Configuration files and prompt templates
- `data/`: Input news data and output folders
- `models/`: Data models for news, topics, and reports
- `reporting/`: Report generation, validation, and formatting
- `runners/`: Pipeline execution modules
- `services/`: LLM and prompt services
- `utils/`: Utility modules for logging, configuration, and file management

## News Data Format

The system expects news data in JSON format. A sample file is provided at `data/sample_news.json`. You need to provide your own news data files following this format:

```json
[
  {
    "_id": 0,
    "title": "News article title",
    "summary": "Brief summary of the article",
    "url": "Source URL",
    "source": "News source name",
    "category": "News category",
    "publishedAt": "Publication date and time"
  },
  ...
]
```

### Required Files and Naming Conventions

To run the system, you need to create your own news data files for each region you want to process:
- For Taiwan: `data/tw_news_YYYYMMDD.json`
- For US: `data/us_news_YYYYMMDD.json`
- For Vietnam: `data/vt_news_YYYYMMDD.json`

Where `YYYYMMDD` is the date in year-month-day format (e.g., `20250406` for April 6, 2025).

### File Naming Rules

1. **Region Code**: The filename must start with a region code:
   - `tw_` for Taiwan
   - `us_` for United States
   - `vt_` for Vietnam

2. **News Indicator**: The region code must be followed by `_news_`

3. **Date Format**: The date must be in `YYYYMMDD` format (year-month-day)

4. **File Extension**: All files must use the `.json` extension

Example of correctly named files:
- `tw_news_20250406.json` - Taiwan news for April 6, 2025
- `us_news_20250406.json` - US news for April 6, 2025
- `vt_news_20250326.json` - Vietnam news for March 26, 2025

The system automatically looks for files with these naming patterns when you specify a region and date in the command-line arguments.

## Usage

Run the pipeline for a specific region:

```
python column_main.py -m once -r tw
```

Options:
- `-m, --mode`: Execution mode (currently only supports `once`)
- `-r, --regions`: Region codes (multiple allowed), e.g., `tw` (Taiwan), `us` (United States), `vt` (Vietnam)
- `-d, --date`: Optional date in `YYYYMMDD` format (defaults to current date)

Example to run for multiple regions with a specific date:
```
python column_main.py -m once -r tw -r us -d 20250406
```

## Data Flow

1. The system loads news data from the specified region and date
2. Topic modeling is performed to identify important themes in the news
3. The most relevant topics are selected for column generation
4. For each topic, relevant news articles are filtered
5. The filtered news is used to generate a comprehensive column
6. The generated content is validated for quality and completeness
7. Reports are saved to the output directory

## Configuration

The system is configured via the `configs/config.yaml` file, which contains settings for different regions and processing parameters.

### Config File Structure

The config file is divided into main sections:

#### System Settings
```yaml
system:
  default_region: us          # Default region to process if not specified
  log_level: INFO             # Default logging level
  max_topics: 5               # Maximum number of topics to process
  max_news_per_topic: 10      # Maximum number of news articles per topic
  min_word_count: 500         # Minimum word count for generated columns
  max_word_count: 2000        # Maximum word count for generated columns
```

#### Region-Specific Settings
Each supported region has its own configuration section:

```yaml
regions:
  tw:  # Taiwan region
    display_name: "Taiwan"
    timezone: "Asia/Taipei"
    main_language: "zh_tw"    # Main language for processing
    input_file: "data/tw_news_{date}.json"
    weighted_sources:         # News sources with custom weights
      "Economy News": 2
      "Anue News": 2
      # Additional weighted sources...
    stopwords:                # Region-specific stopwords for topic modeling
      - "的"
      - "是"
      # Additional stopwords...
  
  # Similar configurations for 'us' and 'vt' regions
```

### Customizing Configuration

To customize the system for your needs:

1. **Adjust system parameters**: Modify the values in the `system` section to change global behavior.

2. **Add new news sources**: Add entries to the `weighted_sources` section for each region to give higher weights to trusted sources.

3. **Customize stopwords**: Add or remove stopwords for each region to improve topic modeling results. Stopwords are common words (like "the", "is", "and") that are filtered out during text processing.

4. **Add new regions**: Copy an existing region configuration and modify it for a new region.

## Output

Generated reports are saved in `data/output/{date}/{region}/`:
- `topics_{date}.json`: Topic modeling results
- `reports_{date}.json`: Generated columns
- `execution_summary_{date}.json`: Execution statistics

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
