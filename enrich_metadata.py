import difflib
import xml.etree.ElementTree as ET
import sys
import os
import time
import logging
import socket
from urllib.error import URLError
try:
    import isbnlib
except ImportError:
    print("Das Paket 'isbnlib' ist nicht installiert. Bitte mit 'pip install isbnlib' nachinstallieren.")
    sys.exit(1)

# Konfiguration: Schwellenwerte für Korrekturen
LEVENSHTEIN_THRESHOLD = 0.7  # Ähnlichkeitsschwelle für Korrekturen (0-1)
CONFIDENCE_THRESHOLD = 0.6   # Konfidenz für Übernahme von isbnlib-Daten (0-1)
CONFLICT_SIMILARITY_THRESHOLD = 0.4  # Unterhalb gilt ein Vergleich als Konflikt
RATE_LIMIT_SECONDS = 0.5  # Wartezeit zwischen isbnlib-Anfragen
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 0.75

# Mapping isbnlib -> MARC-Felder
ISBNLIB_MARC_MAP = {
    "Title": ("245", "a"),
    "Authors": ("100", "a"),
    "Publisher": ("260", "b"),
    "Year": ("260", "c"),
    "Language": ("008", None),  # Sonderfall
}

# Logger einrichten (Datei-basiert)
logger = logging.getLogger("enrich_metadata")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler("enrich_metadata.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
if not logger.handlers:
    logger.addHandler(_fh)

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
    network_errors = 0
    for idx, (record, isbn) in enumerate(isbn_records, 1):
        # ISBN normalisieren (bevorzugt ISBN-13)
        try:
            norm = isbnlib.canonical(isbn) if hasattr(isbnlib, 'canonical') else isbn
            if hasattr(isbnlib, 'to_isbn13'):
                norm13 = isbnlib.to_isbn13(norm) or norm
            else:
                norm13 = norm
        except Exception:
            norm13 = isbn

        meta = None
        # Retry mit Exponential-Backoff
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                meta = isbnlib.meta(norm13)
                break
            except (URLError, socket.timeout) as e:
                network_errors += 1
                wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                msg = f"[{idx}] Netzwerkfehler bei ISBN {norm13} (Versuch {attempt}/{MAX_RETRIES}): {e}. Warte {wait:.2f}s"
                print(msg)
                logger.warning(msg)
                time.sleep(wait)
            except Exception as e:
                # Andere Fehler von isbnlib (z.B. Service-spezifisch)
                network_errors += 1
                msg = f"[{idx}] Fehler bei ISBN {norm13}: {e}"
                print(msg)
                logger.warning(msg)
                break

        # Rate Limit (grundsätzlich zwischen Anfragen)
        time.sleep(RATE_LIMIT_SECONDS)

        if not meta:
            isbn_not_found += 1
            print(f"[{idx}] ISBN nicht gefunden: {norm13}")
            logger.warning(f"ISBN nicht gefunden: {norm13}")
            continue

        # 1) Felder ermitteln (erste Runde)
        fields_info = []  # (key, marc_tag, sub_code, marc_value, marc_subfield)
        for key, (marc_tag, sub_code) in ISBNLIB_MARC_MAP.items():
            marc_value = None
            marc_subfield = None
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
            fields_info.append((key, marc_tag, sub_code, marc_value, marc_subfield))

        # 2) Konfliktquote prüfen
        comparable = 0
        conflicts = 0
        for key, marc_tag, sub_code, marc_value, _ in fields_info:
            meta_value = meta.get(key)
            if key == "Authors" and isinstance(meta_value, list):
                meta_value = ", ".join(meta_value)
            if meta_value is None or str(meta_value).strip() == "":
                continue
            if marc_value is None or str(marc_value).strip() == "":
                continue
            # identische Werte sind kein Konflikt
            if str(marc_value).strip().lower() == str(meta_value).strip().lower():
                comparable += 1
                continue
            # Abkürzungen sind kein Konflikt
            if is_abbreviation(str(marc_value), str(meta_value)):
                comparable += 1
                continue
            # Ähnlichkeit bewerten
            sim = similarity(str(marc_value), str(meta_value))
            comparable += 1
            if sim < CONFLICT_SIMILARITY_THRESHOLD:
                conflicts += 1

        if comparable > 0 and conflicts > (comparable / 2):
            rec_id = next((cf.text for cf in record.findall('controlfield') if cf.get('tag') == '001'), 'unbekannt')
            msg = f"[{idx}] Konfliktquote zu hoch (Konflikte: {conflicts}/{comparable}) für Record {rec_id} (ISBN {isbn}) – Datensatz übersprungen."
            print(msg)
            logger.warning(msg)
            continue

        # 3) Mapping anwenden (zweite Runde)
        for key, marc_tag, sub_code, marc_value, marc_subfield in fields_info:
            meta_value = meta.get(key)
            if key == "Authors" and isinstance(meta_value, list):
                meta_value = ", ".join(meta_value)
            if not meta_value:
                continue
            # Keine Aktion wenn identisch
            if marc_value is not None and str(marc_value).strip() == str(meta_value).strip():
                continue
            # Leeres Feld befüllen
            if (marc_value is None or marc_value == "") and meta_value:
                if sub_code and (marc_subfield is not None):
                    marc_subfield.text = meta_value
                    msg = f"[{idx}] {key}: Leeres Feld befüllt mit '{meta_value}'"
                    change_log.append(msg)
                    logger.info(msg)
            # Abkürzung erkennen und ersetzen
            elif marc_value and is_abbreviation(str(marc_value), str(meta_value)):
                if sub_code and (marc_subfield is not None):
                    marc_subfield.text = meta_value
                    msg = f"[{idx}] {key}: Abkürzung '{marc_value}' ersetzt durch '{meta_value}'"
                    change_log.append(msg)
                    logger.info(msg)
            # Falsch befülltes Feld korrigieren
            else:
                if marc_value:
                    sim = similarity(str(marc_value), str(meta_value))
                    if sim < LEVENSHTEIN_THRESHOLD and sim > CONFIDENCE_THRESHOLD:
                        if sub_code and (marc_subfield is not None):
                            marc_subfield.text = meta_value
                            msg = f"[{idx}] {key}: Wert '{marc_value}' korrigiert zu '{meta_value}' (Ähnlichkeit: {sim:.2f})"
                            change_log.append(msg)
                            logger.info(msg)

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
