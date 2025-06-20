import requests
from bs4 import BeautifulSoup
import os
import json
from xml.etree.ElementTree import Element, SubElement, tostring, Comment
from xml.dom import minidom

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def get_depth_chart_tables(url):
    """
    Fetch the ESPN depth chart page and return the raw HTML of the relevant tables.
    Each table corresponds to a 'ResponsiveTable' div.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching depth chart from {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all depth chart tables (ResponsiveTable containers)
        depth_charts_html = []
        depth_charts = soup.find_all('div', class_='ResponsiveTable')
        
        if not depth_charts:
            print(f"No depth chart tables found for {url}. This might be a temporary issue or the page structure has changed.")
            return None

        for chart in depth_charts:
            # Convert each ResponsiveTable div to its HTML string representation
            # .prettify() helps with readable output
            depth_charts_html.append(chart.prettify())
        
        return depth_charts_html
        
    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error for {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred for {url}: {e}")
        return None

def tables_to_xml(tables, team_name, team_abbrev):
    """
    Convert the tables data structure to XML (kept for reference, not used in main execution as per request).
    This function is unchanged and remains for potential future use if XML output is desired again.
    """
    root = Element('DepthChart')
    team = SubElement(root, 'Team', name=team_name, abbreviation=team_abbrev)
    
    # Group tables by type (Offense, Defense, Special Teams)
    for table in tables: # Note: 'tables' here would need to be the parsed JSON-like structure, not raw HTML
        title = table['title']
        
        # Determine group
        if 'Special' in title:
            group_name = 'Special Teams'
        elif any(pos in title for pos in ['QB', 'RB', 'WR', 'TE', 'OL', 'FB']):
            group_name = 'Offense'
        else:
            group_name = 'Defense'
        
        # Find or create the group element
        group = team.find(f"PositionGroup[@name='{group_name}']")
        if group is None:
            group = SubElement(team, 'PositionGroup', name=group_name)
        
        # Add formation as a comment
        formation_comment = f" Formation: {title} "
        group.append(Comment(formation_comment))
        
        # Add each position
        for pos, players in zip(table['positions'], table['players']):
            position = SubElement(group, 'Position', name=pos)
            
            for depth, player in enumerate(players, 1):
                if player is None:
                    continue
                
                player_elem = SubElement(position, 'Player')
                SubElement(player_elem, 'Depth').text = str(depth)
                SubElement(player_elem, 'Name').text = player['name']
                if player['status']:
                    SubElement(player_elem, 'Status').text = player['status']
    
    return root

# Main execution
if __name__ == "__main__":
    # Define the list of NFL teams with their abbreviations and slugs for URL construction
    nfl_teams = {
        "Arizona Cardinals": {"abbrev": "ari", "slug": "arizona-cardinals"},
        "Atlanta Falcons": {"abbrev": "atl", "slug": "atlanta-falcons"},
        "Baltimore Ravens": {"abbrev": "bal", "slug": "baltimore-ravens"},
        "Buffalo Bills": {"abbrev": "buf", "slug": "buffalo-bills"},
        "Carolina Panthers": {"abbrev": "car", "slug": "carolina-panthers"},
        "Chicago Bears": {"abbrev": "chi", "slug": "chicago-bears"},
        "Cincinnati Bengals": {"abbrev": "cin", "slug": "cincinnati-bengals"},
        "Cleveland Browns": {"abbrev": "cle", "slug": "cleveland-browns"},
        "Dallas Cowboys": {"abbrev": "dal", "slug": "dallas-cowboys"},
        "Denver Broncos": {"abbrev": "den", "slug": "denver-broncos"},
        "Detroit Lions": {"abbrev": "det", "slug": "detroit-lions"},
        "Green Bay Packers": {"abbrev": "gb", "slug": "green-bay-packers"},
        "Houston Texans": {"abbrev": "hou", "slug": "houston-texans"},
        "Indianapolis Colts": {"abbrev": "ind", "slug": "indianapolis-colts"},
        "Jacksonville Jaguars": {"abbrev": "jax", "slug": "jacksonville-jaguars"},
        "Kansas City Chiefs": {"abbrev": "kc", "slug": "kansas-city-chiefs"},
        "Las Vegas Raiders": {"abbrev": "lv", "slug": "las-vegas-raiders"},
        "Los Angeles Chargers": {"abbrev": "lac", "slug": "los-angeles-chargers"},
        "Los Angeles Rams": {"abbrev": "lar", "slug": "los-angeles-rams"},
        "Miami Dolphins": {"abbrev": "mia", "slug": "miami-dolphins"},
        "Minnesota Vikings": {"abbrev": "min", "slug": "minnesota-vikings"},
        "New England Patriots": {"abbrev": "ne", "slug": "new-england-patriots"},
        "New Orleans Saints": {"abbrev": "no", "slug": "new-orleans-saints"},
        "New York Giants": {"abbrev": "nyg", "slug": "new-york-giants"},
        "New York Jets": {"abbrev": "nyj", "slug": "new-york-jets"},
        "Philadelphia Eagles": {"abbrev": "phi", "slug": "philadelphia-eagles"},
        "Pittsburgh Steelers": {"abbrev": "pit", "slug": "pittsburgh-steelers"},
        "San Francisco 49ers": {"abbrev": "sf", "slug": "san-francisco-49ers"},
        "Seattle Seahawks": {"abbrev": "sea", "slug": "seattle-seahawks"},
        "Tampa Bay Buccaneers": {"abbrev": "tb", "slug": "tampa-bay-buccaneers"},
        "Tennessee Titans": {"abbrev": "ten", "slug": "tennessee-titans"},
        "Washington Commanders": {"abbrev": "wsh", "slug": "washington-commanders"},
    }

    output_directory = "team_tables"
    os.makedirs(output_directory, exist_ok=True) # Create the directory if it doesn't exist

    base_url = "https://www.espn.com/nfl/team/depth/_/name/"

    for team_name, info in nfl_teams.items():
        abbrev = info["abbrev"]
        slug = info["slug"]
        team_url = f"{base_url}{abbrev}/{slug}"

        # Now get_depth_chart_tables returns a list of HTML strings
        raw_html_tables = get_depth_chart_tables(team_url)
        
        if raw_html_tables:
            # Save each table as a separate HTML file
            for i, table_html in enumerate(raw_html_tables):
                output_file = os.path.join(output_directory, f"{slug}_depth_chart_table_{i+1}.html")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(table_html)
                
                print(f"Successfully saved table {i+1} for {team_name} to {output_file}")
        else:
            print(f"Failed to retrieve any depth chart tables for {team_name}")
        print("-" * 50) # Separator for readability
