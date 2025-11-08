import xml.etree.ElementTree as ET
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utilities.tag_meanings import tag_meanings

def parse_marc21(file_path, output_file):
    ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
    elements_found = set()

    for event, elem in ET.iterparse(file_path, events=('end',)):
        tag_clean = elem.tag.replace(f"{{{ns['marc']}}}", "")
        
        if tag_clean == "controlfield":
            tag = elem.get('tag')
            elements_found.add((tag, '', ''))

        elif tag_clean == "datafield":
            tag = elem.get('tag')
            ind1 = elem.get('ind1')
            ind2 = elem.get('ind2')
            elements_found.add((tag, ind1, ind2))

        elem.clear()

    with open(output_file, 'w', encoding='utf-8') as f:
        for tag, ind1, ind2 in sorted(elements_found):
            description = tag_meanings.get((tag, ind1, ind2), "Beschreibung unbekannt")
            if ind1 or ind2:
                f.write(f'<datafield tag="{tag}" ind1="{ind1}" ind2="{ind2}"> -> {description}\n')
            else:
                f.write(f'<controlfield tag="{tag}"> -> {description}\n')

if __name__ == '__main__':
    parse_marc21('voebvoll-20241027.xml', 'elements_list.txt')
