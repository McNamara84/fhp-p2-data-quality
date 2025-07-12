import xml.etree.ElementTree as ET

def calculate_008_date_percentage(xml_file_path):
    total_records = 0
    matching_records = 0

    # Iteriere über die Datei und lausche auf das 'end'-Ereignis
    for event, elem in ET.iterparse(xml_file_path, events=('end',)):
        if elem.tag == 'record':
            total_records += 1  # Gesamtanzahl der Records hochzählen
            controlfield_008 = elem.find('./controlfield[@tag="008"]')
            if controlfield_008 is not None and controlfield_008.text is not None and controlfield_008.text.startswith("991231"):
                matching_records += 1  # Anzahl der passenden Records hochzählen
            
            # Speicher freigeben für das verarbeitete Element
            elem.clear()

    if total_records > 0:
        percentage = (matching_records / total_records) * 100
    else:
        percentage = 0

    return percentage

# Verwende die Funktion mit der XML-Datei
xml_file_path = 'voebvoll-20241027.xml'
percentage = calculate_008_date_percentage(xml_file_path)
print(f"Percentage of records with controlfield tag='008' starting '991231': {percentage:.2f}%")