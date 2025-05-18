import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
from tag_meanings import tag_meanings

def parse_marc21_quantity(file_path, output_csv):
    ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
    element_counter = defaultdict(int)
    total_records = 0

    for event, elem in ET.iterparse(file_path, events=('end',)):
        tag_clean = elem.tag.replace(f"{{{ns['marc']}}}", "")
        
        if tag_clean == "record":
            total_records += 1
            
            seen_elements = set()
            
            for child in elem:
                child_tag_clean = child.tag.replace(f"{{{ns['marc']}}}", "")

                if child_tag_clean == "controlfield":
                    tag = child.get('tag')
                    key = (tag, '', '')
                    seen_elements.add(key)

                elif child_tag_clean == "datafield":
                    tag = child.get('tag')
                    ind1 = child.get('ind1')
                    ind2 = child.get('ind2')
                    key = (tag, ind1, ind2)
                    seen_elements.add(key)

            for key in seen_elements:
                element_counter[key] += 1

            elem.clear()

    # Sortieren der Ergebnisse nach Anzahl absteigend
    sorted_elements = sorted(element_counter.items(), key=lambda x: x[1], reverse=True)

    # CSV-Datei mit UTF-8-BOM schreiben für Excel-Kompatibilität
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Element', 'Beschreibung', 'Anzahl Befüllung', 'Befüllung in %'])

        for key, count in sorted_elements:
            tag, ind1, ind2 = key
            desc = tag_meanings.get(key, 'Beschreibung unbekannt')
            percent = (count / total_records) * 100

            if ind1 or ind2:
                element_str = f'<datafield tag="{tag}" ind1="{ind1}" ind2="{ind2}">'
            else:
                element_str = f'<controlfield tag="{tag}">'

            writer.writerow([element_str, desc, count, f'{percent:.2f}%'])

    print(f'Insgesamt {total_records} Datensätze verarbeitet.')
    print(f'Ergebnis gespeichert in: {output_csv}')

if __name__ == '__main__':
    parse_marc21_quantity('voebvoll-20241027.xml', 'metadatenelemente_quantity.csv')
