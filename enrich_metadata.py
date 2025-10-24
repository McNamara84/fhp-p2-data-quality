import difflib
import xml.etree.ElementTree as ET
import sys
import os
import time
import logging
import socket
import threading
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import URLError
try:
    import isbnlib
except ImportError:
    print("Das Paket 'isbnlib' ist nicht installiert. Bitte mit 'pip install isbnlib' nachinstallieren.")
    sys.exit(1)

# DNB-Plugin importieren
try:
    import isbnlib_dnb  # noqa: F401
    # DNB-Service verfügbar machen (registrieren ist nicht nötig, da als Plugin)
    DNB_AVAILABLE = True
    print("✓ isbnlib-dnb geladen - Deutsche Nationalbibliothek wird als Datenquelle verwendet")
except ImportError:
    DNB_AVAILABLE = False
    print("⚠ isbnlib-dnb nicht gefunden - Standard-Services werden verwendet")
    print("  Hinweis: Für bessere Ergebnisse bei deutschsprachiger Literatur installieren Sie 'pip install isbnlib-dnb'")

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

def convert_author_to_marc_format(api_author, marc_author):
    """
    Konvertiert API-Autorennamen (Vorname Nachname) zu MARC-Format (Nachname, Vorname).
    Intelligent: Nur wenn MARC-Eintrag eine Abkürzung ist (z.B. "Nachname, V." oder "Nachname, Max" wenn API "Maximilian" hat).
    
    Args:
        api_author: z.B. "Gotthold Ephraim Lessing" von API
        marc_author: z.B. "Lessing, Gotthold Ephraim" oder "Lessing, G. E." oder "Lessing, Max" aus MARC
        
    Returns:
        Konvertierter Name im MARC-Format oder None wenn keine Konvertierung nötig
    """
    if not api_author or not marc_author:
        return None
    
    # Wenn MARC kein Komma hat, unterschiedliches Format
    if ',' not in marc_author:
        # MARC hat kein Komma -> unterschiedliches Format, versuche Konvertierung
        parts = api_author.strip().split()
        if len(parts) >= 2:
            # Annahme: Letztes Wort ist Nachname
            lastname = parts[-1]
            firstname = " ".join(parts[:-1])
            return f"{lastname}, {firstname}"
        return None
    
    # Extrahiere Nachname und Vorname aus MARC (vor/nach dem Komma)
    marc_parts = marc_author.split(',', 1)
    marc_lastname = marc_parts[0].strip()
    marc_firstname = marc_parts[1].strip() if len(marc_parts) > 1 else ""
    
    # Extrahiere Nachname und Vorname aus API
    api_parts = api_author.strip().split()
    if len(api_parts) < 2:
        return None
    
    api_lastname = api_parts[-1]
    api_firstname = " ".join(api_parts[:-1])
    
    # Prüfe ob der Nachname übereinstimmt
    if marc_lastname.lower() != api_lastname.lower():
        # Unterschiedliche Nachnamen -> nicht konvertieren
        return None
    
    # Prüfe ob Vorname in MARC eine Abkürzung ist (Punkt ODER Längen-Abkürzung)
    has_point_abbreviation = '.' in marc_firstname
    has_length_abbreviation = is_abbreviation(marc_firstname, api_firstname)
    
    if not has_point_abbreviation and not has_length_abbreviation:
        # MARC-Vorname ist bereits vollständig
        return None
    
    # Baue MARC-Format mit vollständigem Vornamen von API
    return f"{marc_lastname}, {api_firstname}"

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
        
        # Spezialbehandlung für Titel: Kombiniere Subfield 'a' + 'b' für vollständigen Vergleich
        if key == "Title" and marc_tag == "245":
            for datafield in record.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    subfield_a = None
                    subfield_b = None
                    subfield_a_elem = None
                    
                    for subfield in datafield.findall("subfield"):
                        if subfield.get("code") == "a":
                            subfield_a = subfield.text.strip() if subfield.text else ""
                            subfield_a_elem = subfield
                        elif subfield.get("code") == "b":
                            subfield_b = subfield.text.strip() if subfield.text else ""
                    
                    # Kombiniere a + b für vollständigen Titel (wie API ihn liefert)
                    if subfield_a:
                        # Entferne Doppelpunkt am Ende von subfield_a wenn vorhanden
                        title_parts = [subfield_a.rstrip(':').rstrip()]
                        if subfield_b:
                            title_parts.append(subfield_b)
                        marc_value = " - ".join(title_parts)  # Trennzeichen wie API (meist " - ")
                        marc_subfield = subfield_a_elem  # Zeiger auf subfield 'a' für Änderungen
                    break
        else:
            # Normale Verarbeitung für andere Felder
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
        
        # SPEZIAL: Authors - Intelligente Format-Behandlung
        if key == "Authors" and meta_value and marc_value:
            # Prüfe ob MARC vollständig ist (keine Abkürzung mit Punkt UND keine Längen-Abkürzung)
            if ',' in marc_value:
                # Extrahiere Vorname aus MARC
                marc_parts = marc_value.split(',', 1)
                marc_firstname = marc_parts[1].strip() if len(marc_parts) > 1 else ""
                
                # Extrahiere Vorname aus API (nach Konvertierung zu MARC-Format)
                api_parts = meta_value.strip().split()
                if len(api_parts) >= 2:
                    api_firstname = " ".join(api_parts[:-1])
                    
                    # Prüfe ob Abkürzung vorliegt (Punkt ODER Länge)
                    has_point_abbreviation = '.' in marc_firstname
                    has_length_abbreviation = is_abbreviation(marc_firstname, api_firstname)
                    
                    if not has_point_abbreviation and not has_length_abbreviation:
                        # MARC ist vollständig -> überspringen
                        continue
            
            # MARC hat Abkürzung oder falsches Format -> konvertiere API zu MARC-Format
            converted_author = convert_author_to_marc_format(meta_value, marc_value)
            if converted_author:
                # Konvertierung erfolgreich -> verwende MARC-formatierte Version
                meta_value = converted_author
            else:
                # Konvertierung fehlgeschlagen (z.B. unterschiedliche Nachnamen) -> überspringen
                continue
        
        # Keine Aktion wenn identisch
        if marc_value is not None and str(marc_value).strip() == str(meta_value).strip():
            continue
        # Leeres Feld befüllen
        if (marc_value is None or marc_value == "") and meta_value:
            if sub_code and (marc_subfield is not None):
                stats['field_stats'][key]['empty_before'] += 1
                stats['field_stats'][key]['filled_after'] += 1
                
                # Bei Authors: Konvertiere Format
                if key == "Authors":
                    # API liefert "Vorname Nachname", konvertiere zu "Nachname, Vorname"
                    parts = meta_value.strip().split()
                    if len(parts) >= 2 and ',' not in meta_value:
                        lastname = parts[-1]
                        firstname = " ".join(parts[:-1])
                        meta_value = f"{lastname}, {firstname}"
                
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


def _enrich_record_inline(idx, elem, isbn, norm13, meta, stats, use_tqdm):
    """
    Inline-Anreicherung eines einzelnen Records (direkt am ET.Element während iterparse).
    Basiert auf _enrich_single_record, aber ohne change_log (da zu memory-intensiv).
    
    WICHTIG: Zählt auch Baseline-Statistiken (total_records, empty_before, etc.)
    
    Args:
        idx: Record-Position (1-based)
        elem: ET.Element des Records
        isbn: Original ISBN
        norm13: Normalisierte ISBN-13
        meta: Metadaten-Dict von isbnlib
        stats: Statistik-Dict (wird in-place modifiziert)
        use_tqdm: Boolean ob tqdm verwendet wird
        
    Returns:
        bool: True wenn Änderungen vorgenommen wurden
    """
    has_changes = False
    
    # Zähle diesen Record für field_stats (total_records)
    for key in ISBNLIB_MARC_MAP.keys():
        stats['field_stats'][key]['total_records'] += 1
    
    # 1) Konfliktquote prüfen (Pre-Check)
    comparable = 0
    conflicts = 0
    
    for key, (marc_tag, sub_code) in ISBNLIB_MARC_MAP.items():
        meta_value = meta.get(key)
        if key == "Authors" and isinstance(meta_value, list):
            meta_value = ", ".join(meta_value)
        if not meta_value or str(meta_value).strip() == "":
            continue
        
        # Hole MARC-Wert
        marc_value = None
        if key == "Title" and marc_tag == "245":
            for datafield in elem.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    subfield_a = None
                    subfield_b = None
                    for subfield in datafield.findall("subfield"):
                        if subfield.get("code") == "a":
                            subfield_a = subfield.text.strip() if subfield.text else ""
                        elif subfield.get("code") == "b":
                            subfield_b = subfield.text.strip() if subfield.text else ""
                    if subfield_a:
                        title_parts = [subfield_a.rstrip(':').rstrip()]
                        if subfield_b:
                            title_parts.append(subfield_b)
                        marc_value = " - ".join(title_parts)
                    break
        else:
            for datafield in elem.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    if sub_code:
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == sub_code:
                                marc_value = subfield.text.strip() if subfield.text else ""
                                break
        
        if not marc_value or str(marc_value).strip() == "":
            continue
        
        # Vergleiche
        if str(marc_value).strip().lower() == str(meta_value).strip().lower():
            comparable += 1
            continue
        if is_abbreviation(str(marc_value), str(meta_value)):
            comparable += 1
            continue
        
        sim = similarity(str(marc_value), str(meta_value))
        comparable += 1
        if sim < CONFLICT_SIMILARITY_THRESHOLD:
            conflicts += 1
    
    # Konfliktquote zu hoch? → Abbrechen
    if comparable > 0 and conflicts > (comparable / 2):
        stats['conflicts_skipped'] += 1
        for key in ISBNLIB_MARC_MAP.keys():
            stats['field_stats'][key]['conflicts'] += 1
        return False
    
    # 2) Felder anreichern
    for key, (marc_tag, sub_code) in ISBNLIB_MARC_MAP.items():
        meta_value = meta.get(key)
        if key == "Authors" and isinstance(meta_value, list):
            meta_value = ", ".join(meta_value)
        if not meta_value:
            continue
        
        # Hole MARC-Wert & Subfield-Element
        marc_value = None
        marc_subfield = None
        
        if key == "Title" and marc_tag == "245":
            for datafield in elem.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    subfield_a_elem = None
                    subfield_b = None
                    for subfield in datafield.findall("subfield"):
                        if subfield.get("code") == "a":
                            subfield_a = subfield.text.strip() if subfield.text else ""
                            subfield_a_elem = subfield
                        elif subfield.get("code") == "b":
                            subfield_b = subfield.text.strip() if subfield.text else ""
                    if subfield_a_elem is not None and subfield.text:
                        title_parts = [subfield.text.rstrip(':').rstrip()]
                        if subfield_b:
                            title_parts.append(subfield_b)
                        marc_value = " - ".join(title_parts)
                        marc_subfield = subfield_a_elem
                    break
        else:
            for datafield in elem.findall("datafield"):
                if datafield.get("tag") == marc_tag:
                    if sub_code:
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == sub_code:
                                marc_value = subfield.text.strip() if subfield.text else ""
                                marc_subfield = subfield
                                break
        
        # SPEZIAL: Authors - Intelligente Format-Behandlung
        if key == "Authors" and meta_value and marc_value:
            if ',' in marc_value:
                marc_parts = marc_value.split(',', 1)
                marc_firstname = marc_parts[1].strip() if len(marc_parts) > 1 else ""
                api_parts = meta_value.strip().split()
                if len(api_parts) >= 2:
                    api_firstname = " ".join(api_parts[:-1])
                    has_point_abbreviation = '.' in marc_firstname
                    has_length_abbreviation = is_abbreviation(marc_firstname, api_firstname)
                    if not has_point_abbreviation and not has_length_abbreviation:
                        continue  # MARC vollständig -> skip
            
            converted_author = convert_author_to_marc_format(meta_value, marc_value)
            if converted_author:
                meta_value = converted_author
            else:
                continue
        
        # Änderungslogik
        if marc_value is not None and str(marc_value).strip() == str(meta_value).strip():
            continue  # Identisch
        
        if (marc_value is None or marc_value == "") and meta_value:
            # Leeres Feld befüllen
            if marc_subfield is not None:
                stats['field_stats'][key]['empty_before'] += 1
                stats['field_stats'][key]['filled_after'] += 1
                
                if key == "Authors" and ',' not in meta_value:
                    parts = meta_value.strip().split()
                    if len(parts) >= 2:
                        lastname = parts[-1]
                        firstname = " ".join(parts[:-1])
                        meta_value = f"{lastname}, {firstname}"
                
                marc_subfield.text = meta_value
                has_changes = True
        
        elif marc_value and is_abbreviation(str(marc_value), str(meta_value)):
            # Abkürzung ersetzen
            if marc_subfield is not None:
                stats['field_stats'][key]['abbreviation_replaced'] += 1
                marc_subfield.text = meta_value
                has_changes = True
        
        else:
            # Korrektur bei Ähnlichkeit
            if marc_value:
                sim = similarity(str(marc_value), str(meta_value))
                if CONFIDENCE_THRESHOLD < sim < LEVENSHTEIN_THRESHOLD:
                    if marc_subfield is not None:
                        stats['field_stats'][key]['corrected'] += 1
                        marc_subfield.text = meta_value
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
    # Versuche Meta-Daten von mehreren Services (DNB bevorzugt, dann Fallbacks)
    services_to_try = ['default', 'goob', 'openl', 'wiki']
    if DNB_AVAILABLE:
        # DNB zuerst, dann die anderen
        services_to_try.insert(0, 'dnb')

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Globalen Rate-Limiter respektieren (vor JEDEM Versuch)
            # Wir holen für jeden Service separat einen Slot.
            for svc in services_to_try:
                _acquire_rate_slot()
                try:
                    meta = isbnlib.meta(norm13, service=svc)
                except Exception as e_meta:
                    # Wenn ein Service einen expliziten Fehler wirft, loggen und zum nächsten Service
                    logger.debug(f"Service {svc} Fehler für ISBN {norm13}: {e_meta}")
                    meta = None

                # Wenn Meta gefunden, abbrechen
                if meta:
                    isbn_cache[norm13] = meta
                    break

            # Wenn Meta gefunden wurde, beende die Retry-Schleife
            if meta:
                retry_attempt = 0 if attempt == 1 else retry_attempt
                break
        except (URLError, socket.timeout) as e:
            retry_attempt = attempt  # Markiere, dass ein Retry nötig war
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            error_msg = f"Netzwerkfehler (Versuch {attempt}/{MAX_RETRIES}): {e}"
            time.sleep(wait)
        except (URLError, socket.timeout) as e:
            # Netzwerkfehler behandeln (wie vorher)
            retry_attempt = attempt  # Markiere, dass ein Retry nötig war
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            error_msg = f"Netzwerkfehler (Versuch {attempt}/{MAX_RETRIES}): {e}"
            time.sleep(wait)
        except Exception as e:
            # Bei 429 (Rate Limit) längere Wartezeit
            if "429" in str(e) or "many requests" in str(e).lower():
                retry_attempt = attempt  # Markiere, dass einRetry nötig war
                wait = BACKOFF_BASE_SECONDS * (3 ** attempt)  # Exponentiell länger
                error_msg = f"Rate Limit (429) erreicht (Versuch {attempt}/{MAX_RETRIES})"
                time.sleep(wait)
            else:
                error_msg = f"Fehler: {e}"
                break

    # Wenn nach allen Versuchen kein Meta gefunden wurde, setze passenden Fehler
    if not meta and not error_msg:
        error_msg = "ISBN nicht gefunden oder keine Metadaten verfügbar"

    return idx, norm13, meta, error_msg, retry_attempt

def main(xml_path, progress_callback=None, check_cancelled=None):
    """
    Hauptfunktion für die Metadaten-Anreicherung mit ITERATIVEM 3-PASS-PARSING.
    Speicherschonend - funktioniert auch mit sehr großen Dateien (>2GB).
    
    Pass 1: Zähle Records & sammle ISBNs (iterativ, kein Speicher-Akkumulation)
    Pass 2: Hole Metadaten parallel von APIs  
    Pass 3: Reichere Records an & schreibe Ausgabedatei (iterativ)
    
    Args:
        xml_path: Pfad zur XML-Datei
        progress_callback: Optional callback(processed, successful, failed, rate_limit_retries, isbn_not_found, conflicts_skipped)
        check_cancelled: Optional callback() -> bool für Abbruchprüfung
        
    Returns:
        dict mit Statistiken (inkl. 'output_path' statt 'tree') oder None bei Fehler
    """
    # Prüfe Dateigröße
    file_size_mb = os.path.getsize(xml_path) / (1024 * 1024)
    print(f"\n📁 Datei: {os.path.basename(xml_path)} ({file_size_mb:.0f} MB)")
    
    if file_size_mb > 500:
        print("   🔄 SPEICHERSCHONENDER 3-PASS-MODUS aktiviert (iteratives Parsing)")
    
    # Statistiken initialisieren
    stats = {
        'total_records': 0,
        'processed_records': 0,
        'successful_enrichments': 0,
        'failed_enrichments': 0,
        'rate_limit_retry_1': 0,
        'rate_limit_retry_2': 0,
        'rate_limit_retry_3': 0,
        'isbn_not_found': 0,
        'conflicts_skipped': 0,
        'multi_isbn_warnings': 0,
        'cancelled': False,
        'field_stats': {
            'Title': {'total_records': 0, 'empty_before': 0, 'filled_after': 0, 'had_abbreviation': 0,
                     'abbreviation_replaced': 0, 'potentially_incorrect': 0, 'corrected': 0, 'conflicts': 0},
            'Authors': {'total_records': 0, 'empty_before': 0, 'filled_after': 0, 'had_abbreviation': 0,
                       'abbreviation_replaced': 0, 'potentially_incorrect': 0, 'corrected': 0, 'conflicts': 0},
            'Publisher': {'total_records': 0, 'empty_before': 0, 'filled_after': 0, 'had_abbreviation': 0,
                         'abbreviation_replaced': 0, 'potentially_incorrect': 0, 'corrected': 0, 'conflicts': 0},
            'Year': {'total_records': 0, 'empty_before': 0, 'filled_after': 0, 'had_abbreviation': 0,
                    'abbreviation_replaced': 0, 'potentially_incorrect': 0, 'corrected': 0, 'conflicts': 0},
        },
        'change_log': []
    }
    
    # ==================== PASS 1: ISBN-Sammlung & Record-Zählung ====================
    print("\n🔍 Pass 1/3: Sammle ISBNs (iterativ, speicherschonend)...")
    
    isbn_map = {}  # isbn -> record_position (1-based)
    record_position = 0
    total_records_in_file = 0
    
    try:
        # Iteratives Parsing - lädt jeweils nur EIN Element
        for event, elem in ET.iterparse(xml_path, events=('end',)):
            if elem.tag == 'record':
                record_position += 1
                total_records_in_file += 1
                
                if record_position % 100000 == 0:
                    print(f"   {record_position:,} Records durchsucht...")
                
                # Suche ISBNs in diesem Record
                isbns = []
                for datafield in elem.findall("datafield"):
                    if datafield.get("tag") == "020":
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == "a" and subfield.text:
                                isbn_text = subfield.text.strip()
                                if isbn_text:
                                    isbns.append(isbn_text)
                
                # Nur eindeutige ISBNs verarbeiten
                if len(isbns) == 1:
                    isbn_map[isbns[0]] = record_position
                elif len(isbns) > 1:
                    stats['multi_isbn_warnings'] += 1
                
                # WICHTIG: Element sofort aus Speicher entfernen
                elem.clear()
                # Note: getprevious() ist lxml-spezifisch, ET hat das nicht
                # Alternativ: root.clear() nutzen wir nicht, da iterparse keinen root behält
    
    except MemoryError:
        print("\n❌ FEHLER: Nicht genug Speicher verfügbar!")
        print("   Die Datei ist extrem groß. Bitte in kleinere Teile aufteilen.")
        return None
    except Exception as e:
        print(f"\n❌ Fehler beim Parsen: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    stats['total_records'] = len(isbn_map)
    print(f"   ✓ {len(isbn_map):,} eindeutige ISBNs gefunden (von {total_records_in_file:,} Records)")
    if stats['multi_isbn_warnings'] > 0:
        print(f"   ⚠  {stats['multi_isbn_warnings']:,} Records mit mehreren ISBNs übersprungen")
    
    # GUI über Gesamtanzahl informieren (nach Pass 1)
    if progress_callback:
        try:
            progress_callback(
                0, 0, 0, 0, 0, 0, 0, 0, total=len(isbn_map)
            )
        except TypeError:
            # Fallback für alte Callback-Signatur ohne 'total' Parameter
            pass
    
    if len(isbn_map) == 0:
        print("❌ Keine ISBNs zum Anreichern gefunden!")
        return stats
    
    # ==================== PASS 2: Metadaten abrufen ====================
    print(f"\n📚 Pass 2/3: Hole Metadaten für {len(isbn_map):,} ISBNs...")
    
    isbn_meta_cache = {}  # isbn -> (norm13, meta)
    
    try:
        from tqdm import tqdm
        use_tqdm = True and not progress_callback
    except ImportError:
        use_tqdm = False
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_isbn_metadata, idx, isbn): (idx, isbn) 
                  for idx, isbn in enumerate(isbn_map.keys(), 1)}
        
        iterator = as_completed(futures)
        if use_tqdm:
            iterator = tqdm(iterator, total=len(isbn_map), desc="Metadaten abrufen")
        
        for future in iterator:
            if check_cancelled and check_cancelled():
                stats['cancelled'] = True
                print("\n⛔ Vom Benutzer abgebrochen!")
                return stats
            
            idx, norm13, meta, error_msg, retry_attempt = future.result()
            
            # Retry-Statistik
            if retry_attempt > 0:
                if retry_attempt == 1:
                    stats['rate_limit_retry_1'] += 1
                elif retry_attempt == 2:
                    stats['rate_limit_retry_2'] += 1
                elif retry_attempt == 3:
                    stats['rate_limit_retry_3'] += 1
            
            if meta:
                original_isbn = futures[future][1]
                isbn_meta_cache[original_isbn] = (norm13, meta)
            elif not error_msg or "429" not in error_msg:
                stats['isbn_not_found'] += 1
            
            if error_msg and "429" not in error_msg:
                stats['failed_enrichments'] += 1
            
            # GUI-Update während Metadaten-Abruf (Pass 2)
            # WICHTIG: 'successful' bleibt 0, da noch keine Anreicherungen stattgefunden haben
            if progress_callback and idx % 10 == 0:
                try:
                    progress_callback(
                        idx, 0, stats['failed_enrichments'],  # successful=0 in Pass 2!
                        stats['rate_limit_retry_1'], stats['rate_limit_retry_2'], stats['rate_limit_retry_3'],
                        stats['isbn_not_found'], stats['conflicts_skipped'],
                        total=len(isbn_map)
                    )
                except TypeError:
                    # Fallback für alte Signatur ohne 'total'
                    progress_callback(
                        idx, 0, stats['failed_enrichments'],  # successful=0 in Pass 2!
                        stats['rate_limit_retry_1'], stats['rate_limit_retry_2'], stats['rate_limit_retry_3'],
                        stats['isbn_not_found'], stats['conflicts_skipped']
                    )
    
    print(f"   ✓ {len(isbn_meta_cache):,} Metadaten erfolgreich abgerufen")
    if stats['isbn_not_found'] > 0:
        print(f"   ⚠  {stats['isbn_not_found']:,} ISBNs nicht gefunden")
    
    # ==================== PASS 3: Anreicherung & Schreiben ====================
    print(f"\n📝 Pass 3/3: Reichere Records an & schreibe Ausgabedatei...")
    
    output_path = xml_path.replace(".xml", "_enriched.xml")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as out_file:
            # XML Header
            out_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out_file.write('<collection xmlns:marc="http://www.loc.gov/MARC21/slim">\n')
            out_file.write(f'<!-- Angereichert am {datetime.now().strftime("%d.%m.%Y %H:%M:%S")} -->\n')
            out_file.write(f'<!-- {len(isbn_meta_cache):,} von {len(isbn_map):,} ISBNs mit Metadaten angereichert -->\n\n')
            
            # Zweiter iterativer Durchlauf - mit Anreicherung
            record_position = 0  # Alle Records in Datei
            isbn_record_position = 0  # Nur Records mit ISBN (= stats['processed_records'])
            enriched_count = 0
            
            for event, elem in ET.iterparse(xml_path, events=('end',)):
                if elem.tag != 'record':
                    continue
                
                record_position += 1
                
                if record_position % 50000 == 0:
                    print(f"   {record_position:,} / {total_records_in_file:,} verarbeitet ({enriched_count:,} angereichert)...")
                
                # Suche ISBN für diesen Record
                current_isbn = None
                for datafield in elem.findall("datafield"):
                    if datafield.get("tag") == "020":
                        for subfield in datafield.findall("subfield"):
                            if subfield.get("code") == "a" and subfield.text:
                                current_isbn = subfield.text.strip()
                                break
                    if current_isbn:
                        break
                
                # Anreichern wenn ISBN vorhanden UND Metadaten verfügbar
                has_changes = False
                if current_isbn and current_isbn in isbn_map:
                    # Zähle nur Records mit ISBN für Progress
                    isbn_record_position += 1
                    
                    if current_isbn in isbn_meta_cache:
                        norm13, meta = isbn_meta_cache[current_isbn]
                        
                        # Inline-Anreicherung (direkt am ET.Element)
                        has_changes = _enrich_record_inline(
                            isbn_record_position, elem, current_isbn, norm13, meta,
                            stats, use_tqdm
                        )
                        
                        if has_changes:
                            enriched_count += 1
                
                # Schreibe Record (angereichert oder unverändert)
                record_str = ET.tostring(elem, encoding='unicode')
                out_file.write(record_str + '\n')
                
                # Element aus Speicher entfernen
                elem.clear()
                # Note: Weitere Speicherbereinigung nicht nötig bei ET.iterparse
                
                # Abbruchprüfung
                if check_cancelled and check_cancelled():
                    stats['cancelled'] = True
                    out_file.write('</collection>\n')
                    print("\n⛔ Vom Benutzer abgebrochen!")
                    return stats
                
                # GUI-Update (nur für Records mit ISBN)
                if progress_callback and isbn_record_position > 0 and isbn_record_position % 100 == 0:
                    try:
                        progress_callback(
                            isbn_record_position, enriched_count, stats['failed_enrichments'],
                            stats['rate_limit_retry_1'], stats['rate_limit_retry_2'], stats['rate_limit_retry_3'],
                            stats['isbn_not_found'], stats['conflicts_skipped'],
                            total=len(isbn_map)
                        )
                    except TypeError:
                        # Fallback für alte Signatur
                        progress_callback(
                            isbn_record_position, enriched_count, stats['failed_enrichments'],
                            stats['rate_limit_retry_1'], stats['rate_limit_retry_2'], stats['rate_limit_retry_3'],
                            stats['isbn_not_found'], stats['conflicts_skipped']
                        )
            
            # XML Footer
            out_file.write('</collection>\n')
        
        stats['successful_enrichments'] = enriched_count
        stats['processed_records'] = isbn_record_position  # Nur Records mit ISBN
        stats['output_path'] = output_path  # WICHTIG: Statt 'tree' für start.py
        
        print(f"\n✅ Fertig! {enriched_count:,} von {record_position:,} Records angereichert")
        print(f"   Ausgabedatei: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Fehler beim Schreiben: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Zusammenfassung
    print("\n=== Zusammenfassung ===")
    print(f"Verarbeitete Records: {stats['processed_records']:,}")
    print(f"Erfolgreiche Anreicherungen: {stats['successful_enrichments']:,}")
    print(f"Fehler: {stats['failed_enrichments']:,}")
    print(f"Rate-Limit Retries: {stats['rate_limit_retry_1'] + stats['rate_limit_retry_2'] + stats['rate_limit_retry_3']:,}")
    print(f"ISBN nicht gefunden: {stats['isbn_not_found']:,}")
    print(f"Konflikte übersprungen: {stats['conflicts_skipped']:,}")
    
    return stats


def export_stats_to_json(stats: dict, xml_path: str, output_path: str) -> str:
    """
    Exportiert Statistiken in eine JSON-Datei.
    
    Args:
        stats: Dictionary mit allen Statistiken
        xml_path: Pfad zur Eingabe-XML-Datei
        output_path: Pfad zur Ausgabe-XML-Datei
        
    Returns:
        Pfad zur erstellten JSON-Datei
    """
    json_path = output_path.replace(".xml", "_stats.json")
    
    # Erstelle exportierbare Struktur (ohne tree und change_log für kompakte JSON)
    export_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "input_file": os.path.basename(xml_path),
            "output_file": os.path.basename(output_path),
            "total_records_in_file": stats.get('total_records', 0),
        },
        "summary": {
            "processed_records": stats.get('processed_records', 0),
            "successful_enrichments": stats.get('successful_enrichments', 0),
            "failed_enrichments": stats.get('failed_enrichments', 0),
            "isbn_not_found": stats.get('isbn_not_found', 0),
            "conflicts_skipped": stats.get('conflicts_skipped', 0),
            "multi_isbn_warnings": stats.get('multi_isbn_warnings', 0),
        },
        "retry_statistics": {
            "rate_limit_retry_1": stats.get('rate_limit_retry_1', 0),
            "rate_limit_retry_2": stats.get('rate_limit_retry_2', 0),
            "rate_limit_retry_3": stats.get('rate_limit_retry_3', 0),
            "total_retries": (
                stats.get('rate_limit_retry_1', 0) +
                stats.get('rate_limit_retry_2', 0) +
                stats.get('rate_limit_retry_3', 0)
            ),
        },
        "field_statistics": stats.get('field_stats', {}),
        "changes": {
            "total_changes": len(stats.get('change_log', [])),
            "change_log": stats.get('change_log', [])[:100]  # Nur erste 100 für Übersicht
        }
    }
    
    # Success rate berechnen
    if export_data['summary']['processed_records'] > 0:
        export_data['summary']['success_rate_percent'] = round(
            (export_data['summary']['successful_enrichments'] / 
             export_data['summary']['processed_records']) * 100, 2
        )
    else:
        export_data['summary']['success_rate_percent'] = 0.0
    
    # JSON speichern
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Statistiken exportiert nach: {json_path}")
    return json_path

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
