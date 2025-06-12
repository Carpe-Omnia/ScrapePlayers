# ScrapePlayers

ScrapePlayers is a tool for scraping player data from sports websites. It automates the process of collecting player statistics, profiles, and other relevant information for analysis or integration into other applications.

## Features

- Fetches player data from supported sports websites
- Parses and structures data for easy use
- Outputs data in common formats (e.g., CSV, JSON)

## Requirements

- Python 3.8+
- `requests` library
- `beautifulsoup4` library

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage
(if you don't want to scrape yourself)

1. Find the data:
team_CSV and combined_depth_charts directories will have all the data your looking for. Collected on June 11th 2025. The table with all the current players is called master_nfl_depth_chart.csv in the combined_depth_charts directory. 

(if you want to scrape yourself)

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/ScrapePlayers.git
    cd ScrapePlayers
    ```

2. Run the scraper:

    ```bash
    python scrape_players.py

    ```

3. Run the processers:

    ```bash
    python process_offenses.py
    python process_defenses.py
    python process_special.py

4. Run the combiners

    ```bash 
    python start_combining.py
    python master_combine.py

5. Check out the data:
you will now have position data for every NFL team and player. The combined depth charts and even a table of every player in the whole league. Do with it what you willl.


## Disclaimer

Use this tool responsibly and respect the terms of service of target websites.

## License

MIT License