import difflib
import xml.etree.ElementTree as ET
import sys
import os
import time
import logging
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
RATE_LIMIT_SECONDS = 0.12  # Globale Mindestzeit zwischen ANY zwei Anfragen (threadsicher)
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2.0  # Längerer Backoff bei 429-Fehlern
MAX_WORKERS = 4  # Reduziert auf 4 parallele Threads, um API-Limits zu respektieren

# Mapping isbnlib -> MARC-Felder
ISBNLIB_MARC_MAP = {
    "Title": ("245", "a"),
    "Authors": ("100", "a"),
    "Publisher": ("260", "b"),
    "Year": ("260", "c"),
    # "Language": ("008", None),  # Sonderfall - deaktiviert für Statistik-Tracking
}

# Logger einrichten (Datei-basiert)
logger = logging.getLogger("enrich_metadata")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler("enrich_metadata.log", mode='w', encoding="utf-8")  # 'w' = überschreiben
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
if not logger.handlers:
    logger.addHandler(_fh)

# In-Memory-Cache für bereits abgefragte ISBNs
isbn_cache = {}

# Globaler, threadsicherer Rate-Limiter (Token-ähnlich)
_rate_lock = threading.Lock()
_next_allowed_time = 0.0  # monotonic Zeit

def _acquire_rate_slot():
    """Stellt sicher, dass zwischen zwei beliebigen Requests mindestens
    RATE_LIMIT_SECONDS liegen (global über alle Threads).
    """
    global _next_allowed_time
    with _rate_lock:
        now = time.monotonic()
        wait = max(0.0, _next_allowed_time - now)
        if wait > 0:
            # Warten außerhalb des Locks verhindert Head-of-line-Blocking anderer Threads
            pass
        else:
            # Slot ist sofort verfügbar
            _next_allowed_time = now + RATE_LIMIT_SECONDS
            return
    # Außerhalb des Locks schlafen und danach Slot finalisieren
    if wait > 0:
        time.sleep(wait)
    with _rate_lock:
        now2 = time.monotonic()
        _next_allowed_time = max(_next_allowed_time, now2 + RATE_LIMIT_SECONDS)

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

def _enrich_single_record(idx, record, isbn, norm13, meta, stats, change_log, use_tqdm, progress_callback):
    """
    Reichert einen einzelnen Record mit ISBN-Metadaten an.
    
    Returns:
        bool: True wenn Änderungen vorgenommen wurden, sonst False
    """
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
        if not use_tqdm and not progress_callback:
            print(msg)
        logger.warning(msg)
        stats['conflicts_skipped'] += 1
        
        # Konflikt-Statistik pro Feld erhöhen
        for key, marc_tag, sub_code, marc_value, _ in fields_info:
            meta_value = meta.get(key)
            if key == "Authors" and isinstance(meta_value, list):
                meta_value = ", ".join(meta_value)
            if meta_value and marc_value:
                if str(marc_value).strip().lower() != str(meta_value).strip().lower():
                    stats['field_stats'][key]['conflicts'] += 1
        
        return False

    # 3) Mapping anwenden (zweite Runde)
    has_changes = False
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
                stats['field_stats'][key]['empty_before'] += 1
                stats['field_stats'][key]['filled_after'] += 1
                marc_subfield.text = meta_value
                msg = f"[{idx}] {key}: Leeres Feld befüllt mit '{meta_value}'"
                change_log.append(msg)
                logger.info(msg)
                has_changes = True
        # Abkürzung erkennen und ersetzen
        elif marc_value and is_abbreviation(str(marc_value), str(meta_value)):
            if sub_code and (marc_subfield is not None):
                stats['field_stats'][key]['abbreviation_replaced'] += 1
                marc_subfield.text = meta_value
                msg = f"[{idx}] {key}: Abkürzung '{marc_value}' ersetzt durch '{meta_value}'"
                change_log.append(msg)
                logger.info(msg)
                has_changes = True
        # Falsch befülltes Feld korrigieren
        else:
            if marc_value:
                sim = similarity(str(marc_value), str(meta_value))
                if sim < LEVENSHTEIN_THRESHOLD and sim > CONFIDENCE_THRESHOLD:
                    if sub_code and (marc_subfield is not None):
                        stats['field_stats'][key]['corrected'] += 1
                        marc_subfield.text = meta_value
                        msg = f"[{idx}] {key}: Wert '{marc_value}' korrigiert zu '{meta_value}' (Ähnlichkeit: {sim:.2f})"
                        change_log.append(msg)
                        logger.info(msg)
                        has_changes = True
    
    return has_changes


def fetch_isbn_metadata(idx, isbn):
    """Fragt Metadaten für eine ISBN ab (mit Retry und Caching)."""
    norm13 = isbn
    try:
        norm = isbnlib.canonical(isbn) if hasattr(isbnlib, 'canonical') else isbn
        if hasattr(isbnlib, 'to_isbn13'):
            norm13 = isbnlib.to_isbn13(norm) or norm
        else:
            norm13 = norm
    except Exception:
        pass

    # Cache prüfen
    if norm13 in isbn_cache:
        return idx, norm13, isbn_cache[norm13], None, 0

    meta = None
    error_msg = None
    retry_attempt = 0  # Welcher Retry-Versuch war erfolgreich (0 = erster Versuch erfolgreich, 1-3 = welcher Retry)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Globalen Rate-Limiter respektieren (vor JEDEM Versuch)
            _acquire_rate_slot()
            meta = isbnlib.meta(norm13)
            isbn_cache[norm13] = meta
            break
        except (URLError, socket.timeout) as e:
            retry_attempt = attempt  # Markiere, dass ein Retry nötig war
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            error_msg = f"Netzwerkfehler (Versuch {attempt}/{MAX_RETRIES}): {e}"
            time.sleep(wait)
        except Exception as e:
            # Bei 429 (Rate Limit) längere Wartezeit
            if "429" in str(e) or "many requests" in str(e).lower():
                retry_attempt = attempt  # Markiere, dass ein Retry nötig war
                wait = BACKOFF_BASE_SECONDS * (3 ** attempt)  # Exponentiell länger
                error_msg = f"Rate Limit (429) erreicht (Versuch {attempt}/{MAX_RETRIES})"
                time.sleep(wait)
            else:
                error_msg = f"Fehler: {e}"
                break

    return idx, norm13, meta, error_msg, retry_attempt

def main(xml_path, progress_callback=None, check_cancelled=None):
    """
    Hauptfunktion für die Metadaten-Anreicherung.
    
    Args:
        xml_path: Pfad zur XML-Datei
        progress_callback: Optional callback(processed, successful, failed, rate_limit_retries, isbn_not_found, conflicts_skipped)
        check_cancelled: Optional callback() -> bool für Abbruchprüfung
        
    Returns:
        dict mit Statistiken oder None bei Fehler
    """
    # Statistiken initialisieren
    stats = {
        'total_records': 0,
        'processed_records': 0,
        'successful_enrichments': 0,
        'failed_enrichments': 0,
        'rate_limit_retry_1': 0,  # Retries beim 1. Versuch
        'rate_limit_retry_2': 0,  # Retries beim 2. Versuch
        'rate_limit_retry_3': 0,  # Retries beim 3. Versuch
        'isbn_not_found': 0,
        'conflicts_skipped': 0,
        'multi_isbn_warnings': 0,
        'cancelled': False,
        'field_stats': {
            'Title': {
                'total_records': 0,
                'empty_before': 0, 
                'filled_after': 0, 
                'had_abbreviation': 0,
                'abbreviation_replaced': 0, 
                'potentially_incorrect': 0,
                'corrected': 0, 
                'conflicts': 0
            },
            'Authors': {
                'total_records': 0,
                'empty_before': 0, 
                'filled_after': 0, 
                'had_abbreviation': 0,
                'abbreviation_replaced': 0, 
                'potentially_incorrect': 0,
                'corrected': 0, 
                'conflicts': 0
            },
            'Publisher': {
                'total_records': 0,
                'empty_before': 0, 
                'filled_after': 0, 
                'had_abbreviation': 0,
                'abbreviation_replaced': 0, 
                'potentially_incorrect': 0,
                'corrected': 0, 
                'conflicts': 0
            },
            'Year': {
                'total_records': 0,
                'empty_before': 0, 
                'filled_after': 0, 
                'had_abbreviation': 0,
                'abbreviation_replaced': 0, 
                'potentially_incorrect': 0,
                'corrected': 0, 
                'conflicts': 0
            },
        }
    }
    
    # Einlesen der XML-Datei
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Fehler beim Einlesen der Datei: {e}")
        return None

    records = root.findall("record")
    total_records = len(records)
    isbn_records = []

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
            stats['multi_isbn_warnings'] += 1
            print(f"Warnung: Datensatz mit mehreren ISBNs gefunden (IDs: {[cf.text for cf in record.findall('controlfield') if cf.get('tag') == '001']}) - übersprungen.")

    stats['total_records'] = len(isbn_records)
    
    print(f"{len(isbn_records)} Datensätze mit ISBN von {total_records} Datensätzen insgesamt eingelesen.")
    if stats['multi_isbn_warnings']:
        print(f"{stats['multi_isbn_warnings']} Datensätze mit mehreren ISBNs wurden übersprungen.")

    # Pre-Enrichment Scan: Baseline-Statistiken erfassen
    print("Pre-Enrichment Scan: Erfasse Baseline-Statistiken...")
    for record, isbn in isbn_records:
        for key, (marc_tag, sub_code) in ISBNLIB_MARC_MAP.items():
            stats['field_stats'][key]['total_records'] += 1
            
            marc_value = None
            for datafield in record.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    if sub_code:
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == sub_code:
                                marc_value = subfield.text.strip() if subfield.text else ""
                                break
            
            # Leer?
            if not marc_value or marc_value == "":
                stats['field_stats'][key]['empty_before'] += 1
            else:
                # Abkürzung? (z.B. "Max." oder sehr kurz)
                if '.' in marc_value or len(marc_value) <= 3:
                    stats['field_stats'][key]['had_abbreviation'] += 1
                
                # Potenziell fehlerhaft? (z.B. Jahr mit nur 2-3 Zeichen)
                if key == 'Year' and len(marc_value) < 4:
                    stats['field_stats'][key]['potentially_incorrect'] += 1

    print("Metadatenabfrage mit isbnlib...")
    change_log = []

    # Parallele Abfrage mit ThreadPoolExecutor
    try:
        from tqdm import tqdm
        use_tqdm = True and not progress_callback  # tqdm nur wenn kein GUI-Callback
    except ImportError:
        use_tqdm = False
        if not progress_callback:
            print("Hinweis: 'tqdm' nicht installiert. Für Fortschrittsbalken bitte 'pip install tqdm' ausführen.")

    # Pipeline-Ansatz: ISBN-Abfrage und Anreicherung verzahnt
    isbn_meta_map = {}  # idx -> (norm13, meta)
    record_map = {idx: (record, isbn) for idx, (record, isbn) in enumerate(isbn_records, 1)}  # idx -> (record, isbn)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_isbn_metadata, idx, isbn): idx for idx, (_, isbn) in enumerate(isbn_records, 1)}
        iterator = as_completed(futures)
        if use_tqdm:
            iterator = tqdm(iterator, total=len(isbn_records), desc="ISBN-Metadaten abrufen & anreichern")

        for future in iterator:
            # Abbruchprüfung
            if check_cancelled and check_cancelled():
                stats['cancelled'] = True
                print("\nAnreicherung vom Benutzer abgebrochen.")
                return stats
            
            idx, norm13, meta, error_msg, retry_attempt = future.result()
            stats['processed_records'] = idx
            
            # Retry-Statistik tracken (retry_attempt ist 0 wenn erfolgreich beim ersten Versuch, 1-3 wenn Retry nötig war)
            if retry_attempt > 0:
                if retry_attempt == 1:
                    stats['rate_limit_retry_1'] += 1
                elif retry_attempt == 2:
                    stats['rate_limit_retry_2'] += 1
                elif retry_attempt == 3:
                    stats['rate_limit_retry_3'] += 1
            
            if error_msg:
                if "429" not in error_msg:  # Nur echte Fehler zählen (429 ist schon über Retry getrackt)
                    stats['failed_enrichments'] += 1
                msg = f"[{idx}] {error_msg} (ISBN {norm13})"
                if not use_tqdm and not progress_callback:
                    print(msg)
                logger.warning(msg)
            
            if not meta:
                stats['isbn_not_found'] += 1
                msg = f"ISBN nicht gefunden: {norm13}"
                if not use_tqdm and not progress_callback:
                    print(f"[{idx}] {msg}")
                logger.warning(msg)
            else:
                isbn_meta_map[idx] = (norm13, meta)
                
                # Anreicherung DIREKT nach erfolgreicher ISBN-Abfrage durchführen
                record, isbn = record_map[idx]
                has_changes = _enrich_single_record(
                    idx, record, isbn, norm13, meta, 
                    stats, change_log, 
                    use_tqdm, progress_callback
                )
                if has_changes:
                    stats['successful_enrichments'] += 1
            
            # GUI-Update
            if progress_callback:
                progress_callback(
                    stats['processed_records'],
                    stats['successful_enrichments'],
                    stats['failed_enrichments'],
                    stats['rate_limit_retry_1'],
                    stats['rate_limit_retry_2'],
                    stats['rate_limit_retry_3'],
                    stats['isbn_not_found'],
                    stats['conflicts_skipped']
                )

    # Zusammenfassung
    stats['change_log'] = change_log
    stats['tree'] = tree  # XML-Tree für Export zurückgeben
    
    print("\n=== Zusammenfassung ===")
    print(f"Verarbeitete Records: {stats['processed_records']}")
    print(f"Erfolgreiche Anreicherungen: {stats['successful_enrichments']}")
    print(f"Fehler: {stats['failed_enrichments']}")
    print(f"Rate-Limit Retries (1/3): {stats['rate_limit_retry_1']}")
    print(f"Rate-Limit Retries (2/3): {stats['rate_limit_retry_2']}")
    print(f"Rate-Limit Retries (3/3): {stats['rate_limit_retry_3']}")
    print(f"ISBN nicht gefunden: {stats['isbn_not_found']}")
    print(f"Konflikte übersprungen: {stats['conflicts_skipped']}")
    print("\nProtokoll der Änderungen:")
    for entry in change_log:
        print(entry)
    
    return stats

if __name__ == "__main__":
    # Standarddatei, kann später per Argument angepasst werden
    xml_path = "example.voebvoll-20241027.xml"
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    if not os.path.exists(xml_path):
        print(f"Datei nicht gefunden: {xml_path}")
        sys.exit(1)
    
    result = main(xml_path)
    if result and not result.get('cancelled'):
        # Optional: XML speichern
        output_path = xml_path.replace(".xml", "_enriched.xml")
        if result.get('tree'):
            result['tree'].write(output_path, encoding='utf-8', xml_declaration=True)
            print(f"\nAngereicherte Datei gespeichert: {output_path}")
    sys.exit(0 if result else 1)
