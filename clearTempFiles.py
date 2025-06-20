import os

def delete_temp_files(directories=None):
    """
    Deletes all .html and .xml files from the specified list of directories.

    Args:
        directories (list): A list of directory paths to clean.
                            Defaults to ['team_CSV', 'team_tables'] if None.
    """
    if directories is None:
        directories = ['team_CSV', 'team_tables']

    print("Starting deletion of temporary HTML/XML files.")

    files_deleted_count = 0
    directories_processed_count = 0

    for directory in directories:
        if not os.path.isdir(directory):
            print(f"Warning: Directory '{directory}' not found. Skipping.")
            continue

        directories_processed_count += 1
        print(f"\nProcessing directory: '{directory}'")

        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            if os.path.isfile(filepath):
                if filename.endswith(".html") or filename.endswith(".xml") or filename.endswith(".csv"):
                    try:
                        os.remove(filepath)
                        print(f"  Deleted: '{filename}'")
                        files_deleted_count += 1
                    except OSError as e:
                        print(f"  Error deleting '{filename}': {e}")
                # else:
                #     print(f"  Skipped: '{filename}' (not .html or .xml)")
            # else:
            #     print(f"  Skipped: '{filename}' (not a file)")

    print("\n--- Deletion Summary ---")
    print(f"Directories processed: {directories_processed_count}")
    print(f"Total files deleted: {files_deleted_count}")
    print("Deletion process complete.")

if __name__ == "__main__":
    delete_temp_files()
