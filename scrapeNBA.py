import requests
from bs4 import BeautifulSoup
import os
import csv
import re

def get_nba_roster_tables(url):
    """
    Fetches the ESPN NBA team roster page and returns the raw HTML of the
    main tables containing player data.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # print(f"Fetching NBA roster data from {url}...") # Commented out to reduce console spam during full league scrape
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # On NBA roster pages, the player tables are typically within 'ResponsiveTable' divs.
        # There might be multiple such divs (e.g., for different sections like "Guards", "Forwards", etc.,
        # or just one main roster table).
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

def parse_nba_roster_data(raw_html_tables, team_name, team_abbrev):
    """
    Parses the raw HTML of multiple NBA roster tables into a flat list of player dictionaries.
    This function is adapted for the ESPN NBA roster page structure to extract
    player name, URL, position, status, and bio stats (age, height, weight, birthplace, birthdate).
    """
    parsed_players = []

    if not raw_html_tables:
        return parsed_players

    # Standardize position groups if tables are split by position (e.g., "Guards")
    # For NBA roster, often it's just one 'Team Roster' table.
    position_group_mapping = {
        "Guards": "G",
        "Forwards": "F",
        "Centers": "C",
        "Team Roster": "Roster", # The main table title
        "Players": "PLYR" # Generic fallback
    }

    for table_html in raw_html_tables:
        soup = BeautifulSoup(table_html, 'html.parser')

        # Identify the title for each table/section (e.g., "Team Roster")
        section_title_tag = soup.find('div', class_='Table__Title')
        section_title = section_title_tag.text.strip() if section_title_tag else "Roster"
        
        # Determine the general position group based on the section title
        general_position_group = position_group_mapping.get(section_title, "Unknown")

        # Find the actual <table> element within the ResponsiveTable div
        inner_table = soup.find('table')
        if not inner_table:
            # print(f"Warning: No <table> found inside ResponsiveTable for section '{section_title}'. Skipping.")
            continue

        # Find the table headers to map column indices to data fields
        # Note: headers are in <thead> -> <tr> -> <th> -> <span>
        headers = [th.find('span').text.strip() for th in inner_table.find_all('thead')[0].find_all('th') if th.find('span')]
        
        # Define expected header mapping to column indices based on the provided HTML
        header_indices = {
            "Name": -1, "POS": -1, "Age": -1, "HT": -1, "WT": -1, 
            "College": -1, "Salary": -1
        }
        for idx, header_text in enumerate(headers):
            # Map actual header text to our standardized keys
            if header_text in header_indices: # Direct match for expected headers
                header_indices[header_text] = idx

        # Find the table body which contains the player rows
        table_body = inner_table.find('tbody')
        if not table_body:
            # print(f"Warning: No <tbody> found in table for section '{section_title}'. Skipping this table.")
            continue

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            
            player_name = None
            player_url = None
            player_status = None
            
            specific_position_from_col = None 
            player_age = None
            player_height = None
            player_weight = None
            player_birthplace = None # Not available on this page
            player_birthdate = None  # Not available on this page
            player_exp = None        # Not available on this page
            player_college = None
            player_salary = None
            
            # Find player name and URL (from the 'Name' column)
            name_cell_idx = header_indices.get('Name', -1) # Added default -1
            if name_cell_idx != -1 and len(cols) > name_cell_idx:
                name_cell_content = cols[name_cell_idx].find('div') # Content is inside a div
                if name_cell_content:
                    player_name_tag = name_cell_content.find('a', class_='AnchorLink')
                    if player_name_tag:
                        player_name = player_name_tag.text.strip()
                        player_url = player_name_tag['href']

                        # Check for status (injury status) - often a sibling span to the AnchorLink
                        status_span = name_cell_content.find('span', class_=lambda x: x and ('injuries-status' in x or 'n8' in x))
                        if status_span and status_span.text.strip():
                            player_status = status_span.text.strip()
                        else:
                            # Fallback: Look for text in parentheses (e.g., jersey number, but could be status)
                            cell_text_content = name_cell_content.get_text(separator=' ', strip=True)
                            match = re.search(r'\(([^)]+)\)$', cell_text_content)
                            if match:
                                potential_status = match.group(1).strip()
                                # Basic filter to avoid jersey numbers or other non-status info
                                if not potential_status.isdigit() and len(potential_status) <= 10:
                                    player_status = potential_status


            # Extract basic bio stats based on identified column indices
            pos_idx = header_indices.get('POS', -1) # Added default -1
            if pos_idx != -1 and len(cols) > pos_idx and cols[pos_idx].div:
                specific_position_from_col = cols[pos_idx].div.text.strip()
            
            age_idx = header_indices.get('Age', -1) # Added default -1
            if age_idx != -1 and len(cols) > age_idx and cols[age_idx].div:
                player_age = cols[age_idx].div.text.strip()
            
            ht_idx = header_indices.get('HT', -1) # Added default -1
            if ht_idx != -1 and len(cols) > ht_idx and cols[ht_idx].div:
                player_height = cols[ht_idx].div.text.strip()
            
            wt_idx = header_indices.get('WT', -1) # Added default -1
            if wt_idx != -1 and len(cols) > wt_idx and cols[wt_idx].div:
                player_weight = cols[wt_idx].div.text.strip()
            
            # These fields are not in the HTML you provided, so their indices will be -1
            # We don't need to explicitly get them if we know they're not there.
            # player_birthplace_idx = header_indices.get('BIRTH_PLACE', -1)
            # player_birthdate_idx = header_indices.get('BIRTHDATE', -1)
            # player_exp_idx = header_indices.get('EXP', -1)
            
            college_idx = header_indices.get('College', -1) # Added default -1
            if college_idx != -1 and len(cols) > college_idx and cols[college_idx].div:
                player_college = cols[college_idx].div.text.strip()

            salary_idx = header_indices.get('Salary', -1) # Added default -1
            if salary_idx != -1 and len(cols) > salary_idx and cols[salary_idx].div:
                player_salary = cols[salary_idx].div.text.strip()

            if player_name:
                player_data = {
                    "team_name": team_name,
                    "team_abbrev": team_abbrev,
                    "section_title": section_title, 
                    "position_name": specific_position_from_col if specific_position_from_col else general_position_group,
                    "player_name": player_name,
                    "depth_label": "Roster", # Always "Roster" from this page type
                    "player_url": player_url,
                    "status": player_status,
                    "age": player_age,
                    "height": player_height,
                    "weight": player_weight,
                    "birth_place": player_birthplace, # Will remain None
                    "birthdate": player_birthdate,   # Will remain None
                    "experience": player_exp,        # Will remain None
                    "college": player_college,
                    "salary": player_salary
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
    
    # Updated preferred header order to include new bio stats and salary
    preferred_headers_order = [
        "team_name", "team_abbrev", "player_name", "position_name", 
        "age", "height", "weight", "experience", "college", "salary",
        "birth_place", "birthdate", "status", "player_url", "section_title"
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

# Main execution for all NBA teams
if __name__ == "__main__":
    # Define the list of NBA teams with their abbreviations and slugs for URL construction
    # This list is manually compiled based on ESPN NBA team URLs.
    nba_teams = {
        "Atlanta Hawks": {"abbrev": "atl", "slug": "atlanta-hawks"},
        "Boston Celtics": {"abbrev": "bos", "slug": "boston-celtics"},
        "Brooklyn Nets": {"abbrev": "bkn", "slug": "brooklyn-nets"},
        "Charlotte Hornets": {"abbrev": "cha", "slug": "charlotte-hornets"},
        "Chicago Bulls": {"abbrev": "chi", "slug": "chicago-bulls"},
        "Cleveland Cavaliers": {"abbrev": "cle", "slug": "cleveland-cavaliers"},
        "Dallas Mavericks": {"abbrev": "dal", "slug": "dallas-mavericks"},
        "Denver Nuggets": {"abbrev": "den", "slug": "denver-nuggets"},
        "Detroit Pistons": {"abbrev": "det", "slug": "detroit-pistons"},
        "Golden State Warriors": {"abbrev": "gs", "slug": "golden-state-warriors"},
        "Houston Rockets": {"abbrev": "hou", "slug": "houston-rockets"},
        "Indiana Pacers": {"abbrev": "ind", "slug": "indiana-pacers"},
        "Los Angeles Clippers": {"abbrev": "lac", "slug": "los-angeles-clippers"},
        "Los Angeles Lakers": {"abbrev": "lal", "slug": "los-angeles-lakers"},
        "Memphis Grizzlies": {"abbrev": "mem", "slug": "memphis-grizzlies"},
        "Miami Heat": {"abbrev": "mia", "slug": "miami-heat"},
        "Milwaukee Bucks": {"abbrev": "mil", "slug": "milwaukee-bucks"},
        "Minnesota Timberwolves": {"abbrev": "min", "slug": "minnesota-timberwolves"},
        "New Orleans Pelicans": {"abbrev": "no", "slug": "new-orleans-pelicans"},
        "New York Knicks": {"abbrev": "ny", "slug": "new-york-knicks"},
        "Oklahoma City Thunder": {"abbrev": "okc", "slug": "oklahoma-city-thunder"},
        "Orlando Magic": {"abbrev": "orl", "slug": "orlando-magic"},
        "Philadelphia 76ers": {"abbrev": "phi", "slug": "philadelphia-76ers"},
        "Phoenix Suns": {"abbrev": "phx", "slug": "phoenix-suns"},
        "Portland Trail Blazers": {"abbrev": "por", "slug": "portland-trail-blazers"}, 
        "Sacramento Kings": {"abbrev": "sac", "slug": "sacramento-kings"},
        "San Antonio Spurs": {"abbrev": "sa", "slug": "san-antonio-spurs"},
        "Toronto Raptors": {"abbrev": "tor", "slug": "toronto-raptors"},
        "Utah Jazz": {"abbrev": "utah", "slug": "utah-jazz"},
        "Washington Wizards": {"abbrev": "wsh", "slug": "washington-wizards"}
    }

    output_directory = "nba_team_data"
    os.makedirs(output_directory, exist_ok=True) # Create the directory if it doesn't exist

    all_raw_players_data = []

    # Updated base URL for NBA rosters
    base_url = "https://www.espn.com/nba/team/roster/_/name/"

    for team_name, info in nba_teams.items():
        abbrev = info["abbrev"]
        slug = info["slug"]
        team_url = f"{base_url}{abbrev}/{slug}"

        print(f"Processing roster for {team_name}...")
        raw_html_tables = get_nba_roster_tables(team_url)
        
        if raw_html_tables:
            players_for_team = parse_nba_roster_data(raw_html_tables, team_name, abbrev)
            if players_for_team:
                all_raw_players_data.extend(players_for_team)
                print(f"Successfully parsed {len(players_for_team)} players for {team_name}.")
            else:
                print(f"No players parsed for {team_name}. Check the page structure and parsing logic.")
        else:
            print(f"Could not retrieve any relevant HTML tables/sections for {team_name}. Skipping.")
        print("-" * 50) # Separator for readability

    # --- Deduplication Logic (for roster) ---
    # Since this is a roster, and players generally appear once,
    # deduplication primarily ensures unique entries per player per team.
    # We will prioritize the first encountered entry if duplicates exist.
    final_players_data = {} # Key: (player_name, team_name), Value: player record

    for player_data in all_raw_players_data:
        player_key = (player_data['player_name'], player_data['team_name'])
        
        if player_key not in final_players_data:
            final_players_data[player_key] = player_data
        # If player already exists, we keep the first one found (no specific depth priority on rosters)

    deduplicated_players = list(final_players_data.values())

    if deduplicated_players:
        output_csv_file = os.path.join(output_directory, "nba_roster_full.csv")
        write_players_to_csv(deduplicated_players, output_csv_file)
        print(f"\nAll NBA roster data collected, deduplicated, and saved to {output_csv_file}")
    else:
        print("\nNo NBA roster data was successfully collected for any team.")
