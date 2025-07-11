import xml.etree.ElementTree as ET

def calculate_leader_01234cam_percentage(xml_file_path):
    total_records = 0
    matching_records = 0

    # Iteriere über die XML-Datei, und lausche auf das 'end'-Ereignis, wenn jedes Element fertig geparst wurde.
    for event, elem in ET.iterparse(xml_file_path, events=('end',)):
        if elem.tag == 'record':
            total_records += 1
            leader = elem.find('leader')
            if leader is not None and leader.text.startswith("01234cam"):
                matching_records += 1
            
            # Speicher freigeben für das verarbeitete Element
            elem.clear()

    if total_records > 0:
        percentage = (matching_records / total_records) * 100
    else:
        percentage = 0

    return percentage

# Verwende die Funktion mit der angegebenen XML-Datei
xml_file_path = 'voebvoll-20241027.xml'
percentage = calculate_leader_01234cam_percentage(xml_file_path)
print(f"Percentage of records with leader starting '01234cam': {percentage:.2f}%")