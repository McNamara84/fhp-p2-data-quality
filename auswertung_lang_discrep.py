import csv
from collections import Counter

def count_language_entries(csv_file: str):
    """Count occurrences of each entry in the 'Language from 041' column and sort them by frequency."""

    language_counter = Counter()

    with open(csv_file, mode='r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Split the languages in the 'Language from 041' field and count each occurrence
            languages = row['Language from 041'].split(',')
            for language in languages:
                language = language.strip().lower()  # Normalize case for consistent counting
                language_counter[language] += 1

    sorted_languages = sorted(language_counter.items(), key=lambda x: x[1], reverse=True)

    # Output only entries that occur more than once
    for language, count in sorted_languages:
        if count > 1:
            print(f"{language}: {count}")
        
if __name__ == '__main__':
    count_language_entries('language_discrepancies.csv') 