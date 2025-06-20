import requests
from bs4 import BeautifulSoup
import os
import json
import re
import csv

def get_depth_chart_container(url):
    """
    Fetch the ESPN MLB team depth chart page and return the raw HTML of the
    main depth chart container div, if found.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # print(f"Fetching data from {url}...") # Commented out to reduce console spam during full league scrape
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The target div identified by the user: <div class="ResponsiveTable ResponsiveTable--fixed-left">
        depth_chart_container = soup.find('div', class_='ResponsiveTable ResponsiveTable--fixed-left')
        
        if not depth_chart_container:
            print(f"No specific depth chart container (ResponsiveTable--fixed-left) found on {url}. Skipping.")
            return None

        # Return the prettified HTML of this specific container
        return depth_chart_container.prettify()
        
    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error for {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred for {url}: {e}")
        return None

def parse_mlb_depth_chart_data(raw_html_container, team_name, team_abbrev):
    """
    Parses the raw HTML of the main depth chart container into a flat list of player dictionaries.
    Each player dictionary will include team information.
    This function is specifically adapted for the ESPN MLB depth chart structure
    with two nested tables.
    """
    parsed_players = []

    if not raw_html_container:
        return parsed_players

    soup = BeautifulSoup(raw_html_container, 'html.parser')
    
    # The provided HTML snippet shows a "Depth Chart" title within the main div
    table_title_tag = soup.find('div', class_='Table__Title')
    section_title = table_title_tag.text.strip() if table_title_tag else "MLB Depth Chart"

    # Find the two internal tables within the main container
    tables = soup.find_all('table')

    if len(tables) < 2:
        # print(f"Warning: Expected at least two tables inside depth chart container for {team_name}, but found {len(tables)}. Skipping.")
        return parsed_players

    # First table contains position names (fixed-left column)
    position_table = tables[0]
    # Second table contains player data for each depth level
    player_data_table = tables[1]

    # --- Extract depth levels from the header of the player_data_table ---
    depth_levels = []
    header_row = player_data_table.find('thead')
    if header_row:
        # Find all <th> elements in the header row
        th_elements = header_row.find_all('th')
        for th in th_elements:
            # The actual header text is inside a span with data-testid="headerTable"
            header_span = th.find('span', {'data-testid': 'headerTable'})
            if header_span and header_span.text.strip():
                depth_levels.append(header_span.text.strip())
    
    if not depth_levels:
        # print(f"Warning: Could not find depth level headers for {team_name}. Falling back to generic labels.")
        # Fallback to generic depth labels if headers are missing
        depth_levels = [f"Depth {i+1}" for i in range(5)] # Assume up to 5 depth levels if headers are missing


    # --- Extract position names from the first table's tbody ---
    position_tbody = position_table.find('tbody')
    # --- Extract player data from the second table's tbody ---
    player_tbody = player_data_table.find('tbody')

    if not position_tbody or not player_tbody:
        # print(f"Error: Could not find tbody in one or both depth chart tables for {team_name}. Skipping.")
        return parsed_players

    position_rows = position_tbody.find_all('tr')
    player_rows = player_tbody.find_all('tr')

    # Iterate through rows, assuming position_rows and player_rows correspond 1:1
    for i in range(min(len(position_rows), len(player_rows))):
        position_row = position_rows[i]
        player_row = player_rows[i]

        # Get position name from the first table's row
        # The position text is inside a span with data-testid="statCell"
        position_name_tag = position_row.find('span', {'data-testid': 'statCell'})
        position_name = position_name_tag.text.strip() if position_name_tag else "Unknown Position"
        
        # Remove any extraneous status info like '<span class="nfl-injuries-status n8"></span>' if present
        position_name = re.sub(r'\s*<span[^>]*class="nfl-injuries-status[^>]*>\s*</span>', '', position_name)
        position_name = position_name.replace('<!-- -->', '').strip() # Clean up HTML comments if BeautifulSoup doesn't remove them fully

        # Get player data from the second table's row (all td elements)
        player_cells = player_row.find_all('td')
        for j, player_cell in enumerate(player_cells):
            player_name_tag = player_cell.find('a', class_='AnchorLink') # Player name is in an AnchorLink
            player_name = player_name_tag.text.strip() if player_name_tag else None
            player_url = player_name_tag['href'] if player_name_tag and 'href' in player_name_tag.attrs else None
            
            player_status = None
            # Status is often in a sibling span, or directly after the name in the text.
            # The HTML shows <span class="nfl-injuries-status n8">IL15</span>
            status_span = player_cell.find('span', class_=lambda x: x and 'nfl-injuries-status' in x)
            if status_span and status_span.text.strip():
                player_status = status_span.text.strip()

            # The cell might also contain '-' if no player is listed for that depth
            cell_text_content = player_cell.get_text(separator=' ', strip=True)
            if cell_text_content == '-' or not player_name:
                player_name = None # Ensure player name is None if it's just a dash

            if player_name:
                # Use the extracted depth level, or fallback to generic
                depth_label = depth_levels[j] if j < len(depth_levels) else f"Depth {j+1}"
                
                player_data = {
                    "team_name": team_name,
                    "team_abbrev": team_abbrev,
                    "section_title": section_title, # This will always be "MLB Depth Chart" in the current structure
                    "position_name": position_name,
                    "player_name": player_name,
                    "depth_label": depth_label,
                    "player_url": player_url,
                    "status": player_status
                }
                parsed_players.append(player_data)
    
    return parsed_players

def write_players_to_csv(players_data, filename):
    """
    Writes a list of player dictionaries to a CSV file.
    Automatically determines headers from the keys of the first dictionary.
    """
    if not players_data:
        print("No player data to write to CSV.")
        return

    # Get all unique headers from all dictionaries to ensure all fields are included
    all_headers = set()
    for player in players_data:
        all_headers.update(player.keys())
    
    # Define a preferred order for headers. Any new headers will be appended alphabetically.
    preferred_headers_order = [
        "team_name", "team_abbrev", "player_name", "position_name", 
        "depth_label", "status", "player_url", "section_title"
    ]
    # Filter preferred headers to only include those actually present in data
    headers = [h for h in preferred_headers_order if h in all_headers]
    # Add any remaining headers that are not in preferred order, sorted alphabetically
    headers.extend(sorted([h for h in all_headers if h not in preferred_headers_order]))


    print(f"Writing {len(players_data)} player records to {filename}...")
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(players_data)
        print("CSV file successfully created.")
    except Exception as e:
        print(f"Error writing to CSV file {filename}: {e}")

# Main execution for all MLB teams
if __name__ == "__main__":
    # Define the list of MLB teams with their abbreviations and slugs for URL construction
    # This list is manually compiled based on ESPN MLB team URLs.
    mlb_teams = {
        "Arizona Diamondbacks": {"abbrev": "ari", "slug": "arizona-diamondbacks"},
        "Atlanta Braves": {"abbrev": "atl", "slug": "atlanta-braves"},
        "Baltimore Orioles": {"abbrev": "bal", "slug": "baltimore-orioles"},
        "Boston Red Sox": {"abbrev": "bos", "slug": "boston-red-sox"},
        "Chicago Cubs": {"abbrev": "chc", "slug": "chicago-cubs"},
        "Chicago White Sox": {"abbrev": "chw", "slug": "chicago-white-sox"},
        "Cincinnati Reds": {"abbrev": "cin", "slug": "cincinnati-reds"},
        "Cleveland Guardians": {"abbrev": "cle", "slug": "cleveland-guardians"},
        "Colorado Rockies": {"abbrev": "col", "slug": "colorado-rockies"},
        "Detroit Tigers": {"abbrev": "det", "slug": "detroit-tigers"},
        "Houston Astros": {"abbrev": "hou", "slug": "houston-astros"},
        "Kansas City Royals": {"abbrev": "kc", "slug": "kansas-city-royals"},
        "Los Angeles Angels": {"abbrev": "laa", "slug": "los-angeles-angels"},
        "Los Angeles Dodgers": {"abbrev": "lad", "slug": "los-angeles-dodgers"},
        "Miami Marlins": {"abbrev": "mia", "slug": "miami-marlins"},
        "Milwaukee Brewers": {"abbrev": "mil", "slug": "milwaukee-brewers"},
        "Minnesota Twins": {"abbrev": "min", "slug": "minnesota-twins"},
        "New York Mets": {"abbrev": "nym", "slug": "new-york-mets"},
        "New York Yankees": {"abbrev": "nyy", "slug": "new-york-yankees"},
        "Oakland Athletics": {"abbrev": "ath", "slug": "oakland-athletics"}, # Updated abbrev
        "Philadelphia Phillies": {"abbrev": "phi", "slug": "philadelphia-phillies"},
        "Pittsburgh Pirates": {"abbrev": "pit", "slug": "pittsburgh-pirates"},
        "San Diego Padres": {"abbrev": "sd", "slug": "san-diego-padres"},
        "San Francisco Giants": {"abbrev": "sf", "slug": "san-francisco-giants"},
        "Seattle Mariners": {"abbrev": "sea", "slug": "seattle-mariners"},
        "St. Louis Cardinals": {"abbrev": "stl", "slug": "st-louis-cardinals"},
        "Tampa Bay Rays": {"abbrev": "tb", "slug": "tampa-bay-rays"},
        "Texas Rangers": {"abbrev": "tex", "slug": "texas-rangers"},
        "Toronto Blue Jays": {"abbrev": "tor", "slug": "toronto-blue-jays"},
        "Washington Nationals": {"abbrev": "wsh", "slug": "washington-nacionals"} # Fixed typo in slug from previous version
    }

    # Define a mapping for depth label to a numeric rank for prioritization
    # Lower number indicates higher priority (e.g., Starter is 1, 2nd is 2)
    depth_rank_map = {
        "Starter": 1, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
        "Depth 1": 1, "Depth 2": 2, "Depth 3": 3, "Depth 4": 4, "Depth 5": 5, "Depth 6": 6,
        "P": 1, "RP": 2, "CL": 3 # Specific pitcher depths if they appear as labels
    }
    # Default high rank for any unmapped depth labels, making them lower priority
    DEFAULT_DEPTH_RANK = 999 

    output_directory = "mlb_team_data"
    os.makedirs(output_directory, exist_ok=True) # Create the directory if it doesn't exist

    all_raw_players_data = []

    base_url = "https://www.espn.com/mlb/team/depth/_/name/"

    for team_name, info in mlb_teams.items():
        abbrev = info["abbrev"]
        slug = info["slug"]
        team_url = f"{base_url}{abbrev}/{slug}"

        print(f"Processing depth chart for {team_name}...")
        raw_html_container = get_depth_chart_container(team_url)
        
        if raw_html_container:
            players_for_team = parse_mlb_depth_chart_data(raw_html_container, team_name, abbrev)
            if players_for_team:
                all_raw_players_data.extend(players_for_team)
                print(f"Successfully parsed {len(players_for_team)} players for {team_name}.")
            else:
                print(f"No players parsed for {team_name}. Check the page structure.")
        else:
            print(f"Could not retrieve depth chart container for {team_name}. Skipping.")
        print("-" * 50) # Separator for readability

    # --- Deduplication and Prioritization Logic ---
    final_players_data = {} # Key: (player_name, team_name), Value: best player record

    for player_data in all_raw_players_data:
        player_key = (player_data['player_name'], player_data['team_name'])
        
        # Get the numeric rank for the current player's depth label
        current_depth_rank = depth_rank_map.get(player_data['depth_label'], DEFAULT_DEPTH_RANK)

        if player_key not in final_players_data:
            # If player not seen before, add them
            final_players_data[player_key] = (current_depth_rank, player_data)
        else:
            # If player seen before, compare depth ranks
            stored_depth_rank, stored_player_data = final_players_data[player_key]
            
            if current_depth_rank < stored_depth_rank:
                # If current player has a better (lower) depth rank, update
                final_players_data[player_key] = (current_depth_rank, player_data)
            # If current_depth_rank == stored_depth_rank, keep the one that was first found
            # If current_depth_rank > stored_depth_rank, keep the stored one

    # Extract just the player data dictionaries from the final_players_data
    deduplicated_players = [data for rank, data in final_players_data.values()]

    if deduplicated_players:
        output_csv_file = os.path.join(output_directory, "mlb_depth_charts_full.csv")
        write_players_to_csv(deduplicated_players, output_csv_file)
        print(f"\nAll MLB depth chart data collected, deduplicated, and saved to {output_csv_file}")
    else:
        print("\nNo MLB depth chart data was successfully collected for any team.")
