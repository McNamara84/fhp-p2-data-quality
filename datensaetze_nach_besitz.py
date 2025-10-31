import xml.etree.ElementTree as ET
from typing import Iterable
from marc_utils import split_records
import csv

def split_by_besitz(input_file: str = 'voebvoll-20241027.xml', output_dir: str = 'nach_besitz', csv_file: str = 'book_counts.csv') -> None:
    """Split records by field 049 subfield ``a`` into separate files."""
    book_counts={} #Counter for Books
    def extractor(elem: ET.Element) -> Iterable[str]:
        vals = []
        for df in elem.findall('datafield[@tag="049"]'):
            for sf in df.findall('subfield'):
                if sf.get('code') == 'a' and sf.text and sf.text.strip():
                    vals.append(sf.text.strip())
        for val in vals or ['unknown']:
            if val in book_counts:
                book_counts[val] += 1
            else:
                book_counts[val] = 1

        return vals or ['unknown']

    split_records(input_file, output_dir, extractor)
    #write book-statistics in csv-File
    with open(csv_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Besitzende Bibliothek', 'Anzahl Datensätze'])

        for category, count in book_counts.items():
            writer.writerow([category, count])

if __name__ == '__main__':
    split_by_besitz()
