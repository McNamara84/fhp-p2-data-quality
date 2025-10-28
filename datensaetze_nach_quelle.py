import xml.etree.ElementTree as ET
from typing import Iterable
import csv
from marc_utils import split_records


def split_by_quelle(input_file: str = 'voebvoll-20241027.xml', output_dir: str = 'nach_quelle', csv_file: str = 'quelle_quantity.csv') -> None:
    """Split records by field 040 values into separate files and count the number of records per category."""

    counts = {'rak': 0, 'rda': 0, 'unknown': 0}
    total_records = 0  # Gesamtanzahl der Datensätze

    def extractor(elem: ET.Element) -> Iterable[str]:
        nonlocal total_records
        total_records += 1

        quelle_vals = []
        for df in elem.findall('datafield[@tag="040"]'):
            for sf in df.findall('subfield'):
                txt = sf.text.strip() if sf.text else ''
                if txt:
                    quelle_vals.append(txt)
        if quelle_vals:
            key = '_'.join(quelle_vals)
            if 'rak' in key:
                counts['rak'] += 1
                return ['rak']
            elif 'rda' in key:
                counts['rda'] += 1
                return ['rda']
        counts['unknown'] += 1
        return ['unknown']

    split_records(input_file, output_dir, extractor)

    # Zusätzliche Datei für detaillierte Zählung
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Katalogisierungsquelle', 'Anzahl Datensätze', 'Anteil in %'])

        for category, count in counts.items():
            percent_total = (count / total_records) * 100 if total_records > 0 else 0
            writer.writerow([category, count, f'{percent_total:.2f}%'])

if __name__ == '__main__':
    split_by_quelle()