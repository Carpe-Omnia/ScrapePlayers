import os
import csv
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def parse_depth_chart_html(html_content):
    """
    Parses the raw HTML content of a single ESPN NFL depth chart table
    and extracts structured data including formation, positions, and players.
    This function is generalized and works for both offense and defense HTML structures.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract the formation title
    title_div = soup.find('div', class_='Table__Title')
    formation_title = title_div.text.strip() if title_div else "Unknown Formation"
    print(f"Parsing formation: {formation_title}")

    # Extract positions from the fixed-left table
    positions = []
    left_table = soup.find('table', class_='Table--fixed-left')
    if left_table:
        for row in left_table.find('tbody').find_all('tr', class_='Table__TR'):
            position_span = row.find('span', {'data-testid': 'statCell'})
            if position_span:
                # Extract only the position abbreviation (e.g., "QB", "RB", "LDE")
                positions.append(position_span.text.split()[0].strip())
    
    if not positions:
        print("Warning: No positions found in the fixed-left table.")
        return None

    # Extract player data from the scrollable table
    player_data_rows = []
    right_table_scroller = soup.find('div', class_='Table__Scroller')
    if right_table_scroller:
        right_table = right_table_scroller.find('table')
        if right_table:
            for row in right_table.find('tbody').find_all('tr', class_='Table__TR'):
                players_in_row = []
                for cell in row.find_all('td', class_='Table__TD'):
                    player_link = cell.find('a', class_='AnchorLink')
                    if player_link:
                        player_name = player_link.text.strip()
                        player_url = player_link['href']
                        player_uid = player_link.get('data-player-uid') # Use .get() for safer access
                        
                        injury_status_span = cell.find('span', class_='nfl-injuries-status')
                        injury_status = injury_status_span.text.strip() if injury_status_span and injury_status_span.text.strip() else None
                        
                        players_in_row.append({
                            'name': player_name,
                            'url': player_url,
                            'uid': player_uid,
                            'status': injury_status
                        })
                    else:
                        # Handle cases where there's no player (e.g., empty depth slot represented by '-')
                        if cell.find('span', {'data-testid': 'statCell'}) and cell.find('span', {'data-testid': 'statCell'}).text.strip() == '-':
                            players_in_row.append(None)
                        else:
                            players_in_row.append(None) # Or an empty dictionary if you prefer to distinguish empty from '-'
                player_data_rows.append(players_in_row)
    else:
        print("Warning: No scroller table found for player data.")
        return None

    # Combine positions with player data, ensuring proper alignment
    # The number of rows in positions and player_data_rows should match
    structured_data = {
        'formation': formation_title,
        'positions_and_players': []
    }

    num_rows = min(len(positions), len(player_data_rows))
    for i in range(num_rows):
        position_name = positions[i]
        depth_players = player_data_rows[i]
        
        structured_data['positions_and_players'].append({
            'position': position_name,
            'players': depth_players
        })
    
    return structured_data

def convert_to_xml(parsed_data):
    """
    Converts the structured depth chart data into an XML Element.
    """
    if not parsed_data:
        return None

    root = Element('DepthChartFormation', name=parsed_data['formation'])

    for pos_entry in parsed_data['positions_and_players']:
        position_elem = SubElement(root, 'Position', name=pos_entry['position'])
        for depth, player in enumerate(pos_entry['players'], 1):
            if player:
                player_elem = SubElement(position_elem, 'Player')
                SubElement(player_elem, 'Depth').text = str(depth)
                SubElement(player_elem, 'Name').text = player['name']
                SubElement(player_elem, 'URL').text = player['url']
                if player['uid']:
                    SubElement(player_elem, 'UID').text = player['uid']
                if player['status']:
                    SubElement(player_elem, 'Status').text = player['status']
            else:
                # Add an empty slot if no player at this depth
                empty_slot = SubElement(position_elem, 'Player')
                empty_slot.set('depth', str(depth))
                empty_slot.set('status', 'Empty Slot')
                
    return root

def convert_to_csv(parsed_data, team_name):
    """
    Converts the structured depth chart data into a CSV string.
    Each row represents a player with their position, depth, name, URL, UID, and status.
    Includes the 'TeamName' column.
    """
    if not parsed_data:
        return None

    csv_rows = []
    # CSV Header
    csv_rows.append(['TeamName', 'Position', 'Depth', 'PlayerName', 'PlayerURL', 'PlayerUID', 'InjuryStatus'])

    for pos_entry in parsed_data['positions_and_players']:
        position_name = pos_entry['position']
        for depth, player in enumerate(pos_entry['players'], 1):
            if player:
                csv_rows.append([
                    team_name,
                    position_name,
                    str(depth),
                    player['name'],
                    player['url'],
                    player['uid'] if player['uid'] else '',
                    player['status'] if player['status'] else ''
                ])
            else:
                # Include empty slots in CSV for completeness
                csv_rows.append([
                    team_name,
                    position_name,
                    str(depth),
                    '', # No player name
                    '', # No player URL
                    '', # No player UID
                    'Empty Slot' # Indicate it's an empty slot
                ])
    
    # Use io.StringIO to write to a string buffer
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_rows)
    return output.getvalue()


if __name__ == "__main__":
    input_directory = "team_tables"
    csv_output_directory = "team_CSV"
    
    # Create the CSV output directory if it doesn't exist
    os.makedirs(csv_output_directory, exist_ok=True)

    print(f"Processing HTML files from: {input_directory}")
    print(f"Saving CSV files to: {csv_output_directory}")
    
    processed_count = 0
    skipped_count = 0

    for filename in os.listdir(input_directory):
        # Process only defense files
        if filename.endswith("_depth_chart_defense.html"):
            
            input_filepath = os.path.join(input_directory, filename)
            
            # Extract team name from filename
            team_slug = filename.replace("_depth_chart_defense.html", "")
            team_name = team_slug.replace("-", " ").title()

            html_content = None
            try:
                with open(input_filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                print(f"\n--- Processing {filename} ({team_name}) ---")
            except FileNotFoundError:
                print(f"Error: The file '{input_filepath}' was not found. Skipping.")
                skipped_count += 1
                continue
            except Exception as e:
                print(f"An error occurred while reading '{input_filepath}': {e}. Skipping.")
                skipped_count += 1
                continue

            if html_content:
                # 1. Parse the HTML content
                parsed_data = parse_depth_chart_html(html_content)

                if parsed_data:
                    # 2. Convert to XML (still outputs to team_tables for quality check)
                    xml_root = convert_to_xml(parsed_data)
                    if xml_root is not None:
                        xml_output = prettify_xml(xml_root)
                        # Optionally print XML to console
                        # print("\n--- XML Output ---")
                        # print(xml_output)
                        
                        output_xml_filename = filename.replace('.html', '.xml')
                        output_xml_filepath = os.path.join(input_directory, output_xml_filename)
                        with open(output_xml_filepath, "w", encoding="utf-8") as f:
                            f.write(xml_output)
                        print(f"XML saved to {output_xml_filepath}")
                    else:
                        print(f"Failed to convert XML for {filename}.")

                    # 3. Convert to CSV (now outputs to team_CSV)
                    csv_output = convert_to_csv(parsed_data, team_name) 
                    if csv_output is not None:
                        # Optionally print CSV to console
                        # print("\n--- CSV Output ---")
                        # print(csv_output)
                        
                        output_csv_filename = filename.replace('.html', '.csv')
                        output_csv_filepath = os.path.join(csv_output_directory, output_csv_filename)
                        with open(output_csv_filepath, "w", encoding="utf-8", newline='') as f:
                            f.write(csv_output)
                        print(f"CSV saved to {output_csv_filepath}")
                        processed_count += 1
                    else:
                        print(f"Failed to convert CSV for {filename}.")
                else:
                    print(f"Failed to parse HTML content for {filename}.")
            else:
                print(f"No HTML content to process in {filename}. Skipping.")
                skipped_count += 1
        else:
            # Skip files that don't match the defense pattern
            pass 

    print("\n--- Processing Summary ---")
    print(f"Defense files processed: {processed_count}")
    print(f"Files skipped (non-defense or error): {skipped_count}")
    print("All relevant defense files processed.")
