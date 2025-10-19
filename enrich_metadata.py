import xml.etree.ElementTree as ET
import sys
import os
try:
    import isbnlib
except ImportError:
    print("Das Paket 'isbnlib' ist nicht installiert. Bitte mit 'pip install isbnlib' nachinstallieren.")
    sys.exit(1)

def main(xml_path):
    # Einlesen der XML-Datei
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Fehler beim Einlesen der Datei: {e}")
        sys.exit(1)

    records = root.findall("record")
    total_records = len(records)
    isbn_records = []
    multi_isbn_warnings = 0
    isbn_not_found = 0

    for record in records:
        isbns = []
        for datafield in record.findall("datafield"):
            if datafield.get("tag") == "020":
                for subfield in datafield.findall("subfield"):
                    if subfield.get("code") == "a" and subfield.text and subfield.text.strip():
                        isbns.append(subfield.text.strip())
        if len(isbns) == 1:
            isbn_records.append((record, isbns[0]))
        elif len(isbns) > 1:
            multi_isbn_warnings += 1
            print(f"Warnung: Datensatz mit mehreren ISBNs gefunden (IDs: {[cf.text for cf in record.findall('controlfield') if cf.get('tag') == '001']}) - übersprungen.")

    print(f"{len(isbn_records)} Datensätze mit ISBN von {total_records} Datensätzen insgesamt eingelesen.")
    if multi_isbn_warnings:
        print(f"{multi_isbn_warnings} Datensätze mit mehreren ISBNs wurden übersprungen.")

    print("Metadatenabfrage mit isbnlib...")
    for idx, (record, isbn) in enumerate(isbn_records, 1):
        meta = isbnlib.meta(isbn)
        if not meta:
            isbn_not_found += 1
            print(f"[{idx}] ISBN nicht gefunden: {isbn}")
        # Für spätere Schritte: meta enthält die angereicherten Daten

    print(f"{isbn_not_found} von {len(isbn_records)} ISBNs konnten nicht angereichert werden.")

if __name__ == "__main__":
    # Standarddatei, kann später per Argument angepasst werden
    xml_path = "example.voebvoll-20241027.xml"
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    if not os.path.exists(xml_path):
        print(f"Datei nicht gefunden: {xml_path}")
        sys.exit(1)
    main(xml_path)
