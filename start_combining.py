import os
import csv
from collections import defaultdict

def combine_team_depth_charts(input_csv_directory="team_CSV", output_combined_directory="combined_depth_charts"):
    """
    Combines individual offense, defense, and special teams CSVs for each NFL team
    into a single CSV per team, handling players in multiple positions.
    Priority for primary position: Offense > Defense > Special Teams.
    Within Special Teams, Punter (P) takes precedence over Holder (H).
    """
    if not os.path.isdir(input_csv_directory):
        print(f"Error: Input directory '{input_csv_directory}' not found.")
        return

    os.makedirs(output_combined_directory, exist_ok=True)
    print(f"Reading CSVs from: {input_csv_directory}")
    print(f"Saving combined CSVs to: {output_combined_directory}")

    # Define processing order and priority for units
    # Lower number indicates higher priority
    unit_priority_map = {
        "_offense.csv": 1,
        "_defense.csv": 2,
        "_special_teams.csv": 3
    }

    # Define specific position priority within Special Teams
    # Lower number indicates higher priority
    special_teams_position_order = {
        'PK': 1,  # Place kicker
        'P': 2,   # Punter (prioritized over H)
        'H': 3,   # Holder
        'LS': 4,  # Long snapper
        'PR': 5,  # Punt Returner
        'KR': 6,  # Kick Returner
        # Add other special teams positions if needed with appropriate priorities
    }

    # Group files by team slug
    team_files = defaultdict(lambda: defaultdict(str)) # team_slug -> {file_type_suffix: filepath}
    for filename in os.listdir(input_csv_directory):
        if filename.endswith(".csv"):
            parts = filename.split('_depth_chart_')
            if len(parts) == 2:
                team_slug = parts[0]
                file_type_suffix = f"_{parts[1]}" # e.g., "_offense.csv", "_defense.csv"
                
                # Check if this file type is one we care about for priority
                found_type = False
                for suffix_key in unit_priority_map.keys():
                    if file_type_suffix.startswith(suffix_key):
                        team_files[team_slug][suffix_key] = os.path.join(input_csv_directory, filename)
                        found_type = True
                        break
                if not found_type:
                    print(f"Warning: Skipping unrecognized CSV file type: {filename}")

    processed_teams_count = 0
    
    # Process each team
    for team_slug, files_info in team_files.items():
        team_name = team_slug.replace("-", " ").title()
        print(f"\n--- Combining data for {team_name} ({team_slug}) ---")

        # Dict to store consolidated player data for this team
        # Key: PlayerUID (should be unique), Value: Dict of player attributes + list of positions
        # Example: { 's:20~l:28~a:3917315': { 'TeamName': '...', 'PlayerName': '...', 'PlayerURL': '...', 'InjuryStatus': '...', 'all_positions': [] } }
        # 'all_positions' will be a list of tuples: (unit_priority, position_name, depth)
        consolidated_players = defaultdict(lambda: {
            'TeamName': team_name,
            'PlayerName': '',
            'PlayerURL': '',
            'PlayerUID': '', # Explicitly store UID in the dict for clarity
            'InjuryStatus': '',
            'all_positions': [] # Store (unit_priority, position_name, depth)
        })

        # Process files in unit priority order
        sorted_file_types = sorted(files_info.keys(), key=lambda x: unit_priority_map.get(x, 999))

        for file_type_suffix in sorted_file_types:
            filepath = files_info[file_type_suffix]
            if not filepath:
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    current_unit_priority = unit_priority_map.get(file_type_suffix, 999)

                    for row in reader:
                        player_uid = row.get('PlayerUID')
                        player_name = row.get('PlayerName')
                        player_url = row.get('PlayerURL')
                        injury_status = row.get('InjuryStatus')
                        position = row.get('Position')
                        depth = row.get('Depth')

                        if not player_uid or player_name == '-' or position == 'Empty Slot': # Handle empty player slots
                            continue
                        
                        # Populate primary player info if not already set, or update if more complete
                        # For players appearing multiple times, the info from the first occurrence (highest priority unit)
                        # will generally stick, or if previous was an empty slot.
                        if not consolidated_players[player_uid]['PlayerName'] or \
                           consolidated_players[player_uid]['PlayerName'] == 'Empty Slot':
                            consolidated_players[player_uid]['PlayerName'] = player_name
                            consolidated_players[player_uid]['PlayerURL'] = player_url
                            consolidated_players[player_uid]['PlayerUID'] = player_uid
                            consolidated_players[player_uid]['InjuryStatus'] = injury_status if injury_status != 'Empty Slot' else ''
                        elif consolidated_players[player_uid]['InjuryStatus'] == 'Empty Slot' and injury_status != 'Empty Slot':
                            consolidated_players[player_uid]['InjuryStatus'] = injury_status # Update status if a real status is found

                        # Add this position and depth to the player's list
                        if position and depth:
                             # Prevent duplicate position entries if a player is listed twice in the same unit
                            if (current_unit_priority, position, depth) not in consolidated_players[player_uid]['all_positions']:
                                consolidated_players[player_uid]['all_positions'].append((current_unit_priority, position, depth))

            except FileNotFoundError:
                print(f"  Warning: File not found: {filepath}")
            except Exception as e:
                print(f"  Error reading {filepath}: {e}")

        # Prepare data for output CSV
        output_rows = []
        header = ['TeamName', 'PrimaryPosition', 'PrimaryDepth', 'PlayerName', 'PlayerURL', 'PlayerUID', 'InjuryStatus', 
                  'Position2', 'Depth2', 'Position3', 'Depth3']
        output_rows.append(header)

        # Custom sorting key for player positions
        def get_position_sort_key(pos_tuple):
            unit_prio = pos_tuple[0]
            position_name = pos_tuple[1]
            depth = pos_tuple[2]

            # Apply special teams position specific priority only if it's a special teams unit
            if unit_prio == unit_priority_map["_special_teams.csv"]:
                # Use defined order for special teams positions, default to high value if not in map
                pos_order_value = special_teams_position_order.get(position_name, 999) 
                return (unit_prio, pos_order_value, depth)
            else:
                # For offense/defense, use alphabetical sort for position name
                return (unit_prio, position_name, depth)


        for player_uid in sorted(consolidated_players.keys()): # Sort by UID for consistent output order
            player_data = consolidated_players[player_uid]
            
            # Sort positions using the custom key
            player_data['all_positions'].sort(key=get_position_sort_key) 

            primary_pos = player_data['all_positions'][0] if player_data['all_positions'] else (None, None, None)
            secondary_pos = player_data['all_positions'][1] if len(player_data['all_positions']) > 1 else (None, None, None)
            tertiary_pos = player_data['all_positions'][2] if len(player_data['all_positions']) > 2 else (None, None, None)

            row = [
                player_data['TeamName'],
                primary_pos[1] if primary_pos[1] else '', # PrimaryPosition
                primary_pos[2] if primary_pos[2] else '', # PrimaryDepth
                player_data['PlayerName'],
                player_data['PlayerURL'],
                player_data['PlayerUID'],
                player_data['InjuryStatus']
            ]
            
            # Add secondary and tertiary positions
            row.extend([
                secondary_pos[1] if secondary_pos[1] else '',
                secondary_pos[2] if secondary_pos[2] else ''
            ])
            row.extend([
                tertiary_pos[1] if tertiary_pos[1] else '',
                tertiary_pos[2] if tertiary_pos[2] else ''
            ])
            
            output_rows.append(row)
        
        # Write combined CSV for the team
        output_filename = f"{team_slug}_combined_depth_chart.csv"
        output_filepath = os.path.join(output_combined_directory, output_filename)
        
        try:
            with open(output_filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(output_rows)
            print(f"  Successfully combined and saved to {output_filepath}")
            processed_teams_count += 1
        except Exception as e:
            print(f"  Error writing combined CSV for {team_name}: {e}")

    print("\n--- Combination Summary ---")
    print(f"Teams processed: {processed_teams_count}")
    print("Combination process complete.")

if __name__ == "__main__":
    combine_team_depth_charts()
