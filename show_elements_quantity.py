import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
from tag_meanings import tag_meanings

# Common language codes used in MARC21 field 008
LANG_CODES = {
    "ger": "Deutsch",
    "eng": "Englisch",
    "fre": "Französisch",
    "spa": "Spanisch",
    "ita": "Italienisch",
    "dut": "Niederländisch",
    "pol": "Polnisch",
    "rus": "Russisch",
    "jpn": "Japanisch",
    "chi": "Chinesisch",
    "por": "Portugiesisch",
}

def parse_008_field(field_content):
    if not field_content:
        return {}
    
    analysis = {}
    
    # Debug: Feld-Länge und Inhalt prüfen
    field_len = len(field_content)
    
    # Datum der Eingabe (Positionen 0-5)
    if field_len > 5:
        date_entered = field_content[0:6]
        if date_entered and date_entered.strip() and date_entered != '      ':
            analysis['Eingabedatum'] = date_entered
    
    # Publikationstyp/Datum-Typ (Position 6)
    if field_len > 6:
        pub_status = field_content[6]
        pub_status_meanings = {
            'b': 'Keine Datumsangaben vorhanden',
            'c': 'Aktuell erscheinend',
            'd': 'Eingestellt',
            'e': 'Detailliertes Datum',
            'i': 'Ungenaues Datum',
            'm': 'Mehrere Daten',
            'n': 'Unbekanntes Datum',
            'p': 'Verteilungsdatum/Produktionsdatum',
            'q': 'Fragliches Datum',
            'r': 'Nachdruck/Reproduktionsdatum',
            's': 'Einzelnes bekanntes Datum',
            't': 'Publikationsdatum und Copyright-Datum',
            'u': 'Unbekannt'
        }
        if pub_status and pub_status in pub_status_meanings:
            analysis['Publikationsstatus'] = f"{pub_status} ({pub_status_meanings[pub_status]})"
    
    # Publikationsjahr 1 (Positionen 7-10)
    if field_len > 10:
        pub_year1 = field_content[7:11]
        if pub_year1 and pub_year1.strip() and pub_year1 != '    ' and pub_year1 != 'uuuu':
            analysis['Publikationsjahr_1'] = pub_year1
    
    # Publikationsjahr 2 (Positionen 11-14)
    if field_len > 14:
        pub_year2 = field_content[11:15]
        if pub_year2 and pub_year2.strip() and pub_year2 != '    ' and pub_year2 != 'uuuu':
            analysis['Publikationsjahr_2'] = pub_year2
    
    # Publikationsland (Positionen 15-17)
    if field_len > 17:
        pub_place = field_content[15:18]
        if pub_place and pub_place.strip() and pub_place != '   ':
            # Häufige Ländercodes erweitert
            country_codes = {
                'gw': 'Deutschland',
                'au': 'Österreich', 
                'sz': 'Schweiz',
                'xxu': 'USA',
                'nyu': 'New York (USA)',
                'cau': 'Kalifornien (USA)',
                'xxk': 'Großbritannien',
                'enk': 'England',
                'fr': 'Frankreich',
                'it': 'Italien',
                'sp': 'Spanien',
                'ne': 'Niederlande',
                'be': 'Belgien',
                'po': 'Polen',
                'ru': 'Russland',
                'ja': 'Japan',
                'ch': 'China'
            }
            country_name = country_codes.get(pub_place.lower(), pub_place)
            analysis['Publikationsland'] = f"{pub_place} ({country_name})"
    
    if field_len >= 39:
        language = field_content[35:38]
        if language and language.strip() and language != '   ':
            lang_name = LANG_CODES.get(language.lower(), language)
            analysis['Sprache'] = f"{language} ({lang_name})"
    
    # Fallback: Prüfe die letzten 3 Zeichen für Sprache (falls Feld kürzer ist)
    if 'Sprache' not in analysis and field_len >= 3:
        # Prüfe die letzten 3 Zeichen
        last_chars = field_content[-3:].strip()
        if last_chars and len(last_chars) == 3:
            if last_chars.lower() in LANG_CODES:
                lang_name = LANG_CODES[last_chars.lower()]
                analysis['Sprache'] = f"{last_chars} ({lang_name})"
    
    return analysis


def parse_969_field(datafield_elem):
    """Parse the local administrative field 969.

    The exact meaning of the codes in this local field differs by institution.
    This function tries to decode common subfields. Unknown values are returned
    as-is.
    """

    analysis = {}

    # Placeholder mappings for common subfield codes. The actual definitions may
    # need to be extended depending on the cataloguing rules in use.
    subfield_meanings = {
        'a': 'Lokaler Status',
        'b': 'Erfassungsquelle',
        'c': 'Bearbeitungsvermerk',
        'd': 'Importkennzeichen',
    }

    for sub in datafield_elem.findall('subfield'):
        code = sub.get('code')
        value = sub.text or ''

        if code in subfield_meanings:
            key = subfield_meanings[code]
            analysis[key] = value.strip()
        else:
            analysis[f'Subfeld_{code}'] = value.strip()

    return analysis

def parse_marc21_quantity(file_path, output_csv):
    ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
    element_counter = defaultdict(int)
    field_008_counter = defaultdict(int)  # Für detaillierte 008-Analyse
    field_969_counter = defaultdict(int)  # Für detaillierte 969-Analyse
    
    # Neue Counter für distinkte Werte
    pub_status_values = defaultdict(int)
    pub_country_values = defaultdict(int)
    language_values = defaultdict(int)
    
    total_records = 0
    total_008_fields = 0
    total_969_fields = 0

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
                    
                    # Spezielle Behandlung für 008-Feld
                    if tag == '008':
                        total_008_fields += 1
                        field_content = child.text or ''
                        analysis = parse_008_field(field_content)
                        
                        # Zähle jedes gefundene Unterelement
                        for subfield_name, value in analysis.items():
                            field_008_counter[subfield_name] += 1
                            
                            # Sammle distinkte Werte für spezielle Felder
                            if subfield_name == 'Publikationsstatus':
                                pub_status_values[value] += 1
                            elif subfield_name == 'Publikationsland':
                                pub_country_values[value] += 1
                            elif subfield_name == 'Sprache':
                                language_values[value] += 1
                        
                        # Debug: Zeige erste paar 008-Felder zur Kontrolle
                        if total_008_fields <= 5:
                            print(f"008-Feld #{total_008_fields}: '{field_content}' (Länge: {len(field_content)})")
                            print(f"  Positionen 0-5 (Eingabedatum): '{field_content[0:6] if len(field_content) > 5 else 'zu kurz'}'")
                            print(f"  Position 6 (Pub-Status): '{field_content[6] if len(field_content) > 6 else 'zu kurz'}'")
                            print(f"  Positionen 7-10 (Jahr 1): '{field_content[7:11] if len(field_content) > 10 else 'zu kurz'}'")
                            print(f"  Positionen 11-14 (Jahr 2): '{field_content[11:15] if len(field_content) > 14 else 'zu kurz'}'")
                            print(f"  Positionen 15-17 (Land): '{field_content[15:18] if len(field_content) > 17 else 'zu kurz'}'")
                            print(f"  Positionen 35-37 (Sprache): '{field_content[35:38] if len(field_content) > 37 else 'zu kurz'}'")
                            print(f"  Letzte 3 Zeichen: '{field_content[-3:] if len(field_content) >= 3 else 'zu kurz'}'")
                            print(f"Analyse: {analysis}")
                            print()

                elif child_tag_clean == "datafield":
                    tag = child.get('tag')
                    ind1 = child.get('ind1')
                    ind2 = child.get('ind2')
                    key = (tag, ind1, ind2)
                    seen_elements.add(key)

                    if tag == '969':
                        total_969_fields += 1
                        analysis = parse_969_field(child)

                        for subfield_name in analysis:
                            field_969_counter[subfield_name] += 1

                        if total_969_fields <= 5:
                            print(f"969-Feld #{total_969_fields}: {analysis}")

            for key in seen_elements:
                element_counter[key] += 1

            elem.clear()

    # Sortieren der Ergebnisse nach Anzahl absteigend
    sorted_elements = sorted(element_counter.items(), key=lambda x: x[1], reverse=True)
    sorted_008_elements = sorted(field_008_counter.items(), key=lambda x: x[1], reverse=True)
    sorted_969_elements = sorted(field_969_counter.items(), key=lambda x: x[1], reverse=True)

    # Hauptdatei: CSV-Datei mit UTF-8-BOM schreiben für Excel-Kompatibilität
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

    # Zusätzliche Datei für detaillierte 008-Feld-Analyse
    output_008_csv = output_csv.replace('.csv', '_008_details.csv')
    with open(output_008_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['008-Unterfeld', 'Anzahl Befüllung', 'Befüllung in % (von allen Datensätzen)', 'Befüllung in % (von 008-Feldern)'])

        for subfield_name, count in sorted_008_elements:
            percent_total = (count / total_records) * 100
            percent_008 = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
            writer.writerow([subfield_name, count, f'{percent_total:.2f}%', f'{percent_008:.2f}%'])

    # Zusätzliche Datei für detaillierte 969-Feld-Analyse
    output_969_csv = output_csv.replace('.csv', '_969_details.csv')
    with open(output_969_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['969-Unterfeld', 'Anzahl Befüllung', 'Befüllung in % (von allen Datensätzen)', 'Befüllung in % (von 969-Feldern)'])

        for subfield_name, count in sorted_969_elements:
            percent_total = (count / total_records) * 100
            percent_969 = (count / total_969_fields) * 100 if total_969_fields > 0 else 0
            writer.writerow([subfield_name, count, f'{percent_total:.2f}%', f'{percent_969:.2f}%'])

    # Zusätzliche Datei für distinkte 008-Werte
    output_008_values_csv = output_csv.replace('.csv', '_008_values.csv')
    with open(output_008_values_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Kategorie', 'Wert', 'Anzahl', 'Anteil in %'])
        
        # Publikationsstatus
        sorted_pub_status = sorted(pub_status_values.items(), key=lambda x: x[1], reverse=True)
        for value, count in sorted_pub_status:
            percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
            writer.writerow(['Publikationsstatus', value, count, f'{percent:.2f}%'])
        
        # Publikationsländer (nur wenn welche gefunden wurden)
        if pub_country_values:
            writer.writerow(['', '', '', ''])  # Leerzeile nur wenn nötig
            sorted_countries = sorted(pub_country_values.items(), key=lambda x: x[1], reverse=True)
            for value, count in sorted_countries:
                percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
                writer.writerow(['Publikationsland', value, count, f'{percent:.2f}%'])
        
        # Sprachen (nur wenn welche gefunden wurden)
        if language_values:
            writer.writerow(['', '', '', ''])  # Leerzeile nur wenn nötig
            sorted_languages = sorted(language_values.items(), key=lambda x: x[1], reverse=True)
            for value, count in sorted_languages:
                percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
                writer.writerow(['Sprache', value, count, f'{percent:.2f}%'])

    print(f'Insgesamt {total_records} Datensätze verarbeitet.')
    print(f'Davon {total_008_fields} mit 008-Feld.')
    print(f'Davon {total_969_fields} mit 969-Feld.')
    print(f'Hauptergebnis gespeichert in: {output_csv}')
    print(f'008-Feld-Details gespeichert in: {output_008_csv}')
    print(f'008-Distinkte-Werte gespeichert in: {output_008_values_csv}')
    print(f'969-Feld-Details gespeichert in: {output_969_csv}')
    
    # Statistik-Übersicht für 008-Felder
    if sorted_008_elements:
        print(f'\nTop 5 am häufigsten befüllte 008-Unterfelder:')
        for subfield_name, count in sorted_008_elements[:5]:
            percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
            print(f'  {subfield_name}: {count} ({percent:.1f}% der 008-Felder)')

    if sorted_969_elements:
        print(f'\nTop 5 am häufigsten befüllte 969-Unterfelder:')
        for subfield_name, count in sorted_969_elements[:5]:
            percent = (count / total_969_fields) * 100 if total_969_fields > 0 else 0
            print(f'  {subfield_name}: {count} ({percent:.1f}% der 969-Felder)')
    
    # Zusätzliche Statistiken für distinkte Werte
    print(f'\nDistinkte Werte gefunden:')
    print(f'  Publikationsstatus: {len(pub_status_values)} verschiedene Werte')
    print(f'  Publikationsländer: {len(pub_country_values)} verschiedene Länder')
    print(f'  Sprachen: {len(language_values)} verschiedene Sprachen')
    
    if language_values:
        sorted_languages = sorted(language_values.items(), key=lambda x: x[1], reverse=True)
        print(f'\nTop 5 häufigste Sprachen:')
        for value, count in sorted_languages[:5]:
            percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
            print(f'  {value}: {count} ({percent:.1f}%)')
    
    if pub_country_values:
        sorted_countries = sorted(pub_country_values.items(), key=lambda x: x[1], reverse=True)
        print(f'\nTop 5 häufigste Publikationsländer:')
        for value, count in sorted_countries[:5]:
            percent = (count / total_008_fields) * 100 if total_008_fields > 0 else 0
            print(f'  {value}: {count} ({percent:.1f}%)')

if __name__ == '__main__':
    parse_marc21_quantity('voebvoll-20241027.xml', 'metadatenelemente_quantity.csv')
