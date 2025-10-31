import xml.etree.ElementTree as ET
import csv

def count_049_tags(input_file: str = 'voebvoll-20241027.xml', csv_file: str = 'bib_counts.csv') -> None:
    """Count occurrences of the 049 tag in each record and save results to a CSV file, including record ID from tag 001."""

    occurrences_049 = []

    context = ET.iterparse(input_file, events=("end",))
    _, root = next(context)  # Holen des root-Elements

    for event, elem in context:
        if elem.tag == "record":
            # Finde die Datensatz-ID
            record_id = elem.findtext('controlfield[@tag="001"]', default='Unknown').strip()
            
            # Zähle 049-Tags
            count_049 = len(elem.findall('datafield[@tag="049"]'))
            occurrences_049.append((record_id, count_049))
            
            # Elemente bereinigen, um Speicher freizugeben
            elem.clear()
            root.clear()
    # Sortiere die Ergebnisse nach der Anzahl der 049-Tags, absteigend
    occurrences_049.sort(key=lambda x: x[1], reverse=True)
    
    # Schreibe Ergebnisse in CSV-Datei
    with open(csv_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Datensatz ID', 'Anzahl 049'])
        writer.writerows(occurrences_049)

if __name__ == '__main__':
    count_049_tags()