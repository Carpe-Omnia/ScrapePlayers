import os
import csv

def create_master_depth_chart_csv(input_directory="combined_depth_charts", output_filename="master_nfl_depth_chart.csv"):
    """
    Combines all individual team depth chart CSVs from a specified directory
    into a single master CSV file.
    """
    if not os.path.isdir(input_directory):
        print(f"Error: Input directory '{input_directory}' not found. Please ensure it exists and contains combined team CSVs.")
        return

    output_filepath = os.path.join(input_directory, output_filename) # Save master CSV in the same directory as combined CSVs
    
    print(f"Combining CSVs from: {input_directory}")
    print(f"Outputting master CSV to: {output_filepath}")

    all_files = [f for f in os.listdir(input_directory) if f.endswith(".csv") and f != output_filename]
    
    if not all_files:
        print("No combined team CSV files found to combine. Make sure you've run the 'combine_team_depth_charts' script first.")
        return

    # Sort files to ensure consistent order, though not strictly necessary for combination
    all_files.sort()

    header_written = False
    rows_written_count = 0

    try:
        with open(output_filepath, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile)

            for i, filename in enumerate(all_files):
                filepath = os.path.join(input_directory, filename)
                print(f"  Processing: {filename}")

                with open(filepath, 'r', encoding='utf-8', newline='') as infile:
                    reader = csv.reader(infile)
                    
                    header = next(reader) # Read header
                    
                    if not header_written:
                        writer.writerow(header) # Write header only once
                        header_written = True

                    for row in reader:
                        writer.writerow(row)
                        rows_written_count += 1
        
        print("\n--- Master CSV Creation Summary ---")
        print(f"Successfully created master CSV: {output_filepath}")
        print(f"Total rows written (excluding header): {rows_written_count}")
        print("Combination process complete.")

    except Exception as e:
        print(f"An error occurred during master CSV creation: {e}")


if __name__ == "__main__":
    create_master_depth_chart_csv()
