import difflib
import xml.etree.ElementTree as ET
import sys
import os
try:
    import isbnlib
except ImportError:
    print("Das Paket 'isbnlib' ist nicht installiert. Bitte mit 'pip install isbnlib' nachinstallieren.")
    sys.exit(1)

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
    """Prüft, ob value eine Abkürzung von full_value ist.
    - Keine Abkürzung, wenn Werte identisch sind
    - Numerische Werte (z. B. Jahre) sind keine Abkürzungen
    - True bei 'A.' vs 'Anna' (Punkt-Ende)
    - True bei Präfix, wenn value deutlich kürzer ist (z. B. 'Max' vs 'Maximilian')
    """
    if not value or not full_value:
        return False
    if value.strip().lower() == str(full_value).strip().lower():
        return False
    # Jahreszahlen oder rein numerische Strings nicht als Abkürzung behandeln
    if value.strip().isdigit() and str(full_value).strip().isdigit():
        return False
    v = value.strip()
    f = str(full_value).strip()
    if v.endswith('.'):
        return True
    # nur wenn v spürbar kürzer ist
    if len(v) < len(f) and f.lower().startswith(v.lower()):
        # z.B. 'Max' (3) vs 'Maximilian' (10) -> Verhältnis < 0.6
        return len(v) / max(1, len(f)) <= 0.6
    return False

def similarity(a, b):
    # Levenshtein-Ähnlichkeit
    return difflib.SequenceMatcher(None, a, b).ratio()

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
            marc_subfield = None
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
            # Keine Aktion wenn identisch
            if marc_value is not None and str(marc_value).strip() == str(meta_value).strip():
                continue
            # Leeres Feld befüllen
            if (marc_value is None or marc_value == "") and meta_value:
                # MARC-Feld existiert, Subfield leer
                if sub_code and (marc_subfield is not None):
                    marc_subfield.text = meta_value
                    change_log.append(f"[{idx}] {key}: Leeres Feld befüllt mit '{meta_value}'")
                # MARC-Feld existiert nicht: kann später ergänzt werden
            # Abkürzung erkennen und ersetzen
            elif marc_value and is_abbreviation(marc_value, meta_value):
                if sub_code and (marc_subfield is not None):
                    marc_subfield.text = meta_value
                    change_log.append(f"[{idx}] {key}: Abkürzung '{marc_value}' ersetzt durch '{meta_value}'")
            # Falsch befülltes Feld korrigieren
            else:
                if marc_value:
                    sim = similarity(marc_value, meta_value)
                    if sim < LEVENSHTEIN_THRESHOLD and sim > CONFIDENCE_THRESHOLD:
                        if sub_code and (marc_subfield is not None):
                            marc_subfield.text = meta_value
                            change_log.append(f"[{idx}] {key}: Wert '{marc_value}' korrigiert zu '{meta_value}' (Ähnlichkeit: {sim:.2f})")

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
