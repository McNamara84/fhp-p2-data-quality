import xml.etree.ElementTree as ET
import csv

LANG_CODES = {
    "ara": {"arabisch", "arabic", "ara"},
    "eng": {"englisch", "english", "eng"},
    "ger": {"deutsch", "deutsh", "deutsch (ger)", "ger", "detsch", "deutch", "deutrsch", "deusch", "deutsch+", "deustch"},
    "rus": {"russisch", "russian", "rus"},
    "ukr": {"ukrainisch", "ukrainian", "ukr"},
    "nds": {"plattdeutsch"},
}

def replace_name_with_code(element: ET.Element, changed_count: int) -> int:
    """Sprachennamen mit Sprachcodes ersetzen"""
    for field_041 in element.findall('datafield[@tag="041"]'):
        subfield_a = field_041.find('subfield[@code="a"]')
        if subfield_a is not None:
            lang_name = subfield_a.text.strip().lower()
            for code, names in LANG_CODES.items():
                if lang_name in names:
                    subfield_a.text = code
                    changed_count += 1
                    break
    return changed_count

def enrich_language(input_file: str, output_file: str = 'language_discrepancies.csv'):
    tree = ET.parse(input_file)
    root = tree.getroot()

    discrepancies = []
    changed_count = 0
    initial_count = 0

    for elem in root.findall('record'):
        fields_041 = elem.findall('datafield[@tag="041"]')
        if fields_041:
            initial_count += len(fields_041)
        
        changed_count = replace_name_with_code(elem, changed_count)
        
        # Hole den Inhalt des controlfield tag="008"
        field_008_content = elem.findtext('controlfield[@tag="008"]', default='').strip()
        language_from_008 = field_008_content[35:38].lower()

        field_041 = elem.find('datafield[@tag="041"]')
        language_from_041 = None

        # Wenn ||| im Feld 008, aktualisiere den Sprachcode
        if field_041 is not None:
            language_from_041 = field_041.findtext('subfield[@code="a"]', default='').strip().lower()
            
            if language_from_008 == "|||":
                if language_from_041 in LANG_CODES:
                    new_field_008_content = field_008_content[:35] + language_from_041 + field_008_content[38:]
                    field_008 = elem.find('controlfield[@tag="008"]')
                    if field_008 is not None:
                        field_008.text = new_field_008_content
            elif language_from_041 != language_from_008:
                discrepancies.append((language_from_008, language_from_041))
        else:
            # Einfügen eines neuen 041-Feldes, wenn es nicht existiert
            field_040 = elem.find('datafield[@tag="040"]')
            new_field_041 = ET.Element("datafield", tag="041", ind1=" ", ind2=" ")
            subfield_a = ET.SubElement(new_field_041, "subfield", code="a")
            subfield_a.text = language_from_008

            if field_040 is not None:
                position_to_insert = list(elem).index(field_040) + 1
                elem.insert(position_to_insert, new_field_041)
            else:
                elem.append(new_field_041)

    print(f"Initially filled 041 fields count: {initial_count}")
    print(f"Changed 041 fields count: {changed_count}")
    
    # Schreibe die Diskrepanzen in eine CSV-Datei
    with open(output_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['Language from 008', 'Language from 041'])
        writer.writerows(discrepancies)
    # Speichere die bearbeitete XML-Datei
    tree.write('enriched_languages.xml', encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    enrich_language('voebvoll-20241027.xml')