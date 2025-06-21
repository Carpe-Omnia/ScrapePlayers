import requests
from bs4 import BeautifulSoup
import os
import csv
import re

def get_nhl_roster_tables(url):
    """
    Fetches the ESPN NHL team roster page and returns the raw HTML of the
    main tables containing player data.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # print(f"Fetching NHL roster data from {url}...") # Commented out to reduce console spam during full league scrape
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # NHL roster pages often have multiple tables, typically one for each position group (Forwards, Defensemen, Goalies).
        # These are usually wrapped in 'ResponsiveTable' divs.
        
        all_tables_containers = soup.find_all('div', class_='ResponsiveTable')
        
        if not all_tables_containers:
            print(f"No 'ResponsiveTable' divs found on {url}. Page structure might be different. Skipping.")
            return None

        # Return the prettified HTML of all found relevant containers.
        raw_html_tables = [container.prettify() for container in all_tables_containers]
        return raw_html_tables
        
    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error for {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred for {url}: {e}")
        return None

def parse_nhl_roster_data(raw_html_tables, team_name, team_abbrev):
    """
    Parses the raw HTML of multiple NHL roster tables into a flat list of player dictionaries.
    This function is adapted for the ESPN NHL roster page structure, where each ResponsiveTable
    div represents a position group (Centers, Left Wings, Right Wings, Defense, Goalies).
    It now correctly extracts player name, URL, specific position, and bio stats from nested elements.
    """
    parsed_players = []

    if not raw_html_tables:
        return parsed_players

    # Map section titles to standard position abbreviations (used as the primary position)
    position_mapping = {
        "Centers": "C",
        "Left Wings": "LW",
        "Right Wings": "RW",
        "Defense": "D",
        "Goalies": "G",
        "Forwards": "F", # In case a combined 'Forwards' section exists
        "Players": "PLYR" # Generic fallback
    }

    for table_html in raw_html_tables:
        soup = BeautifulSoup(table_html, 'html.parser')

        # Identify the title for each table/section (e.g., "Centers", "Left Wings")
        section_title_tag = soup.find('div', class_='Table__Title')
        section_title = section_title_tag.text.strip() if section_title_tag else "Unknown Section"
        
        # Determine the position name based on the section title
        position_name = position_mapping.get(section_title, "Unknown")

        # Find the actual <table> element within the ResponsiveTable div
        inner_table = soup.find('table')
        if not inner_table:
            # print(f"Warning: No <table> found inside ResponsiveTable for section '{section_title}'. Skipping.")
            continue

        # Find the table body which contains the player rows
        table_body = inner_table.find('tbody')
        if not table_body:
            # print(f"Warning: No <tbody> found in table for section '{section_title}'. Skipping this table.")
            continue

        rows = table_body.find_all('tr')
        for row in rows:
            # All <td> columns for the current row
            cols = row.find_all('td')
            
            player_name = None
            player_url = None
            player_status = None
            
            player_age = None
            player_height = None
            player_weight = None
            player_shot = None
            player_birthplace = None
            player_birthdate = None

            if len(cols) > 1: # Ensure there are enough columns
                # Player name and URL are in the second <td> column (index 1)
                player_info_cell = cols[1]
                player_name_tag = player_info_cell.find('a', class_='AnchorLink')
                if player_name_tag:
                    player_name = player_name_tag.text.strip()
                    player_url = player_name_tag['href']

                    # Check for status (injury status)
                    status_span = player_info_cell.find('span', class_=lambda x: x and ('injuries-status' in x or 'n8' in x))
                    if status_span and status_span.text.strip():
                        player_status = status_span.text.strip()
                    else:
                        # Fallback: Look for text in parentheses in the overall player info cell text content
                        cell_text_content = player_info_cell.get_text(separator=' ', strip=True)
                        match = re.search(r'\(([^)]+)\)$', cell_text_content)
                        if match:
                            potential_status = match.group(1).strip()
                            if len(potential_status) <= 10 and not potential_status.isdigit():
                                player_status = potential_status

                # Extract basic bio stats from other columns based on their index
                # Age (index 2)
                if len(cols) > 2 and cols[2].div:
                    player_age = cols[2].div.text.strip()
                # Height (index 3)
                if len(cols) > 3 and cols[3].div:
                    player_height = cols[3].div.text.strip()
                # Weight (index 4)
                if len(cols) > 4 and cols[4].div:
                    player_weight = cols[4].div.text.strip()
                # Shot (index 5)
                if len(cols) > 5 and cols[5].div:
                    player_shot = cols[5].div.text.strip()
                # Birth Place (index 6)
                if len(cols) > 6 and cols[6].div:
                    player_birthplace = cols[6].div.text.strip()
                # Birthdate (index 7)
                if len(cols) > 7 and cols[7].div:
                    player_birthdate = cols[7].div.text.strip()

            if player_name:
                player_data = {
                    "team_name": team_name,
                    "team_abbrev": team_abbrev,
                    "section_title": section_title, # e.g., "Centers", "Left Wings"
                    "position_name": position_name, # Derived from section title (C, LW, RW, D, G)
                    "player_name": player_name,
                    "depth_label": "Roster", # No explicit depth on roster pages, so 'Roster'
                    "player_url": player_url,
                    "status": player_status,
                    "age": player_age,
                    "height": player_height,
                    "weight": player_weight,
                    "shot": player_shot,
                    "birth_place": player_birthplace,
                    "birthdate": player_birthdate
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

    all_headers = set()
    for player in players_data:
        all_headers.update(player.keys())
    
    # Updated preferred header order to include new bio stats
    preferred_headers_order = [
        "team_name", "team_abbrev", "player_name", "position_name", 
        "age", "height", "weight", "shot", "birth_place", "birthdate",
        "depth_label", "status", "player_url", "section_title"
    ]
    headers = [h for h in preferred_headers_order if h in all_headers]
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

# Main execution for all NHL teams
if __name__ == "__main__":
    # Define the list of all NHL teams with their abbreviations and slugs for URL construction
    # This list is manually compiled based on ESPN NHL team URLs.
    nhl_teams = {
        "Anaheim Ducks": {"abbrev": "ana", "slug": "anaheim-ducks"},
        "Arizona Coyotes": {"abbrev": "ari", "slug": "arizona-coyotes"}, # Note: May become Utah in future
        "Boston Bruins": {"abbrev": "bos", "slug": "boston-bruins"},
        "Buffalo Sabres": {"abbrev": "buf", "slug": "buffalo-sabres"},
        "Calgary Flames": {"abbrev": "cgy", "slug": "calgary-flames"},
        "Carolina Hurricanes": {"abbrev": "car", "slug": "carolina-hurricanes"},
        "Chicago Blackhawks": {"abbrev": "chi", "slug": "chicago-blackhawks"},
        "Colorado Avalanche": {"abbrev": "col", "slug": "colorado-avalanche"},
        "Columbus Blue Jackets": {"abbrev": "cbj", "slug": "columbus-blue-jackets"},
        "Dallas Stars": {"abbrev": "dal", "slug": "dallas-stars"},
        "Detroit Red Wings": {"abbrev": "det", "slug": "detroit-red-wings"},
        "Edmonton Oilers": {"abbrev": "edm", "slug": "edmonton-oilers"},
        "Florida Panthers": {"abbrev": "fla", "slug": "florida-panthers"},
        "Los Angeles Kings": {"abbrev": "la", "slug": "los-angeles-kings"},
        "Minnesota Wild": {"abbrev": "min", "slug": "minnesota-wild"},
        "Montreal Canadiens": {"abbrev": "mtl", "slug": "montreal-canadiens"},
        "Nashville Predators": {"abbrev": "nsh", "slug": "nashville-predators"},
        "New Jersey Devils": {"abbrev": "nj", "slug": "new-jersey-devils"},
        "New York Islanders": {"abbrev": "nyi", "slug": "new-york-islanders"},
        "New York Rangers": {"abbrev": "nyr", "slug": "new-york-rangers"},
        "Ottawa Senators": {"abbrev": "ott", "slug": "ottawa-senators"},
        "Philadelphia Flyers": {"abbrev": "phi", "slug": "philadelphia-flyers"},
        "Pittsburgh Penguins": {"abbrev": "pit", "slug": "pittsburgh-penguins"},
        "San Jose Sharks": {"abbrev": "sj", "slug": "san-jose-sharks"},
        "Seattle Kraken": {"abbrev": "sea", "slug": "seattle-kraken"},
        "St. Louis Blues": {"abbrev": "stl", "slug": "st-louis-blues"},
        "Tampa Bay Lightning": {"abbrev": "tb", "slug": "tampa-bay-lightning"},
        "Toronto Maple Leafs": {"abbrev": "tor", "slug": "toronto-maple-leafs"},
        "Vancouver Canucks": {"abbrev": "van", "slug": "vancouver-canucks"},
        "Vegas Golden Knights": {"abbrev": "vgk", "slug": "vegas-golden-knights"},
        "Washington Capitals": {"abbrev": "wsh", "slug": "washington-capitals"},
        "Winnipeg Jets": {"abbrev": "wpg", "slug": "winnipeg-jets"}
    }
    
    output_directory = "nhl_team_data"
    os.makedirs(output_directory, exist_ok=True) # Create the directory if it doesn't exist

    all_raw_players_data = []

    base_url = "https://www.espn.com/nhl/team/roster/_/name/"

    for team_name, info in nhl_teams.items():
        abbrev = info["abbrev"]
        slug = info["slug"]
        team_url = f"{base_url}{abbrev}/{slug}"

        print(f"Processing roster for {team_name}...")
        raw_html_tables = get_nhl_roster_tables(team_url)
        
        if raw_html_tables:
            players_for_team = parse_nhl_roster_data(raw_html_tables, team_name, abbrev)
            if players_for_team:
                all_raw_players_data.extend(players_for_team)
                print(f"Successfully parsed {len(players_for_team)} players for {team_name}.")
            else:
                print(f"No players parsed for {team_name}. Check the page structure and parsing logic.")
        else:
            print(f"Could not retrieve any relevant HTML tables/sections for {team_name}. Skipping.")
        print("-" * 50) # Separator for readability

    # --- Deduplication Logic (for roster) ---
    # In NHL rosters, players generally appear once. If a player is listed in multiple
    # positional sections (e.g., as both LW and C if the roster is split), this will
    # keep the first entry encountered for that player on that team.
    depth_rank_map = {
        "Roster": 1, # All players initially get this rank, no explicit depth to prioritize
    }
    DEFAULT_DEPTH_RANK = 999 

    final_players_data = {} # Key: (player_name, team_name), Value: best player record

    for player_data in all_raw_players_data:
        player_key = (player_data['player_name'], player_data['team_name'])
        
        current_depth_rank = depth_rank_map.get(player_data['depth_label'], DEFAULT_DEPTH_RANK)

        if player_key not in final_players_data:
            final_players_data[player_key] = (current_depth_rank, player_data)
        else:
            stored_depth_rank, stored_player_data = final_players_data[player_key]
            # Since all are "Roster" depth, this comparison won't typically change
            # which entry is kept, effectively keeping the first one encountered.
            if current_depth_rank < stored_depth_rank: 
                final_players_data[player_key] = (current_depth_rank, player_data)

    deduplicated_players = [data for rank, data in final_players_data.values()]

    if deduplicated_players:
        output_csv_file = os.path.join(output_directory, "nhl_roster_full.csv")
        write_players_to_csv(deduplicated_players, output_csv_file)
        print(f"\nAll NHL roster data collected, deduplicated, and saved to {output_csv_file}")
    else:
        print("\nNo NHL roster data was successfully collected for any team.")
