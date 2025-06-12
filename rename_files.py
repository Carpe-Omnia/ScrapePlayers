import os

def rename_depth_chart_files(directory="team_tables"):
    """
    Renames depth chart HTML files in the specified directory.
    Files ending with '_depth_chart_table_1.html' become '_depth_chart_offense.html',
    '_depth_chart_table_2.html' become '_depth_chart_defense.html', and
    '_depth_chart_table_3.html' become '_depth_chart_special_teams.html'.
    """
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    print(f"Starting file renaming in directory: '{directory}'")

    # Define the renaming patterns
    rename_patterns = {
        "_depth_chart_table_1.html": "_depth_chart_offense.html",
        "_depth_chart_table_2.html": "_depth_chart_defense.html",
        "_depth_chart_table_3.html": "_depth_chart_special_teams.html"
    }

    files_renamed_count = 0
    files_skipped_count = 0

    for filename in os.listdir(directory):
        old_filepath = os.path.join(directory, filename)

        # Ensure it's a file and not a directory
        if os.path.isfile(old_filepath):
            renamed = False
            for old_suffix, new_suffix in rename_patterns.items():
                if filename.endswith(old_suffix):
                    # Construct the new filename by replacing the suffix
                    new_filename = filename.replace(old_suffix, new_suffix)
                    new_filepath = os.path.join(directory, new_filename)
                    
                    try:
                        os.rename(old_filepath, new_filepath)
                        print(f"Renamed: '{filename}' -> '{new_filename}'")
                        files_renamed_count += 1
                        renamed = True
                        break # Move to the next file once a match is found and renamed
                    except OSError as e:
                        print(f"Error renaming '{filename}': {e}")
                        renamed = True # Mark as processed, even if error, to avoid re-attempting
                        break

            if not renamed:
                print(f"Skipped: '{filename}' (no matching rename pattern)")
                files_skipped_count += 1
        else:
            print(f"Skipped: '{filename}' (not a file)")
            files_skipped_count += 1

    print("\n--- Renaming Summary ---")
    print(f"Files renamed: {files_renamed_count}")
    print(f"Files skipped: {files_skipped_count}")
    print("Renaming process complete.")


if __name__ == "__main__":
    rename_depth_chart_files()
