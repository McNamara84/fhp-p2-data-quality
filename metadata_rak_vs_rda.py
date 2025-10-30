import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
from tag_meanings import tag_meanings 

def parse_marc21_quantity(file_paths, output_csv):
    ns = {'marc': 'http://www.loc.gov/MARC21/slim'}

    # Dictionary für jede Datei
    counters = {
        'rda': defaultdict(int),
        'rak': defaultdict(int),
        'unknown': defaultdict(int)
    }
    total_records = {
        'rda': 0,
        'rak': 0,
        'unknown': 0
    }

    # Zuordnung der Datei zur entsprechenden Kategorie
    for file_path in file_paths:
        category = 'unknown'
        if 'rda' in file_path:
            category = 'rda'
        elif 'rak' in file_path:
            category = 'rak'

        for event, elem in ET.iterparse(file_path, events=('end',)):
            tag_clean = elem.tag.replace(f"{{{ns['marc']}}}", "")

            if tag_clean == "record":
                total_records[category] += 1
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
                    counters[category][key] += 1

                elem.clear()

    # Hauptdatei: CSV-Datei mit UTF-8-BOM schreiben für Excel-Kompatibilität
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        header = [
            'Element', 'Beschreibung',
            'Anzahl Befüllung rda', 'Befüllung rda in %',
            'Anzahl Befüllung rak', 'Befüllung rak in %',
            'Anzahl Befüllung unknown', 'Befüllung unbekannt in %'
        ]
        writer.writerow(header)

        # Berechnen und für alle Schlüssel schreiben
        all_keys = set(counters['rda'].keys()).union(counters['rak'].keys(), counters['unknown'].keys())
        for key in sorted(all_keys):
            tag, ind1, ind2 = key
            desc = tag_meanings.get(key, 'Beschreibung unbekannt')

            def write_values(category):
                count = counters[category][key]
                percent = (count / total_records[category] * 100) if total_records[category] > 0 else 0
                return [count, f'{percent:.2f}%']

            element_str = f'<controlfield tag="{tag}">' if ind1 == '' and ind2 == '' else f'<datafield tag="{tag}" ind1="{ind1}" ind2="{ind2}">'
            row = [element_str, desc] + write_values('rda') + write_values('rak') + write_values('unknown')

            writer.writerow(row)

if __name__ == '__main__':
    xml_files = ['rda.xml', 'rak.xml', 'unknown.xml']
    parse_marc21_quantity(xml_files, 'metadatenelemente_nach_quelle.csv')