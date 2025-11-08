import csv

def count_occurrences(csv_file: str, target_value: int = 1) -> int:
    """Count how often a specific value occurs in the 'Anzahl 049' column."""

    count = 0

    with open(csv_file, mode='r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=';')
        
        for row in reader:
            try:
                anzahl_049 = int(row['Anzahl 049'])
                if anzahl_049 == target_value:
                    count += 1
            except ValueError:
                # Skip rows with invalid integer values
                pass

    return count

if __name__ == '__main__':
    occurrences = count_occurrences('possession_counts.csv')
    print(f"Anzahl der Vorkommen von 1 in 'Anzahl 049': {occurrences}")
