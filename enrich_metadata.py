import difflib

# Konfiguration: Schwellenwerte für Korrekturen
LEVENSHTEIN_THRESHOLD = 0.7  # Ähnlichkeitsschwelle für Korrekturen (0-1)
CONFIDENCE_THRESHOLD = 0.6   # Konfidenz für Übernahme von isbnlib-Daten (0-1)

# Mapping isbnlib -> MARC-Felder
ISBNLIB_MARC_MAP = {
    "Title": ("245", "a"),
    "Authors": ("100", "a"),
    "Publisher": ("260", "b"),
    "Year": ("260", "c"),
    "Language": ("008", None),  # Sonderfall
}

def is_abbreviation(value, full_value):
    # Prüft, ob value eine Abkürzung von full_value ist
    if not value or not full_value:
        return False
    # z.B. "A." vs "Anna" oder "Max" vs "Maximilian"
    return value.endswith(".") or (len(value) <= 4 and full_value.lower().startswith(value.lower()))

def similarity(a, b):
    # Levenshtein-Ähnlichkeit
    return difflib.SequenceMatcher(None, a, b).ratio()
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
    change_log = []
    for idx, (record, isbn) in enumerate(isbn_records, 1):
        meta = isbnlib.meta(isbn)
        if not meta:
            isbn_not_found += 1
            print(f"[{idx}] ISBN nicht gefunden: {isbn}")
            continue

        # Mapping und Anreicherung
        for key, (marc_tag, sub_code) in ISBNLIB_MARC_MAP.items():
            marc_value = None
            # MARC-Feld suchen
            for datafield in record.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    if sub_code:
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == sub_code:
                                marc_value = subfield.text.strip() if subfield.text else ""
                                marc_subfield = subfield
                                break
                    else:
                        marc_value = None  # Sonderfall
            # Wert aus isbnlib
            meta_value = meta.get(key)
            if not meta_value:
                continue
            # Autoren als Liste behandeln
            if key == "Authors" and isinstance(meta_value, list):
                meta_value = ", ".join(meta_value)
            # Leeres Feld befüllen
            if (marc_value is None or marc_value == "") and meta_value:
                # MARC-Feld existiert, Subfield leer
                if sub_code and marc_subfield:
                    marc_subfield.text = meta_value
                    change_log.append(f"[{idx}] {key}: Leeres Feld befüllt mit '{meta_value}'")
                # MARC-Feld existiert nicht: kann später ergänzt werden
            # Abkürzung erkennen und ersetzen
            elif marc_value and is_abbreviation(marc_value, meta_value):
                if sub_code and marc_subfield:
                    marc_subfield.text = meta_value
                    change_log.append(f"[{idx}] {key}: Abkürzung '{marc_value}' ersetzt durch '{meta_value}'")
            # Falsch befülltes Feld korrigieren
            elif marc_value and similarity(marc_value, meta_value) < LEVENSHTEIN_THRESHOLD and similarity(marc_value, meta_value) > CONFIDENCE_THRESHOLD:
                if sub_code and marc_subfield:
                    marc_subfield.text = meta_value
                    change_log.append(f"[{idx}] {key}: Wert '{marc_value}' korrigiert zu '{meta_value}' (Ähnlichkeit: {similarity(marc_value, meta_value):.2f})")

    print(f"{isbn_not_found} von {len(isbn_records)} ISBNs konnten nicht angereichert werden.")
    print("Protokoll der Änderungen:")
    for entry in change_log:
        print(entry)

if __name__ == "__main__":
    # Standarddatei, kann später per Argument angepasst werden
    xml_path = "example.voebvoll-20241027.xml"
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    if not os.path.exists(xml_path):
        print(f"Datei nicht gefunden: {xml_path}")
        sys.exit(1)
    main(xml_path)
