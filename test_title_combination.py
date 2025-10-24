import xml.etree.ElementTree as ET

# Simuliere einen MARC-Record mit aufgeteiltem Titel
xml_str = '''<record>
    <datafield tag="245" ind1="0" ind2="0">
        <subfield code="a">Roter Stern über Deutschland :</subfield>
        <subfield code="b">sowjetische Truppen in der DDR</subfield>
    </datafield>
</record>'''

record = ET.fromstring(xml_str)

# Test Subfield-Kombination
for datafield in record.findall('datafield'):
    if datafield.get('tag') == '245':
        subfield_a = None
        subfield_b = None
        
        for subfield in datafield.findall('subfield'):
            if subfield.get('code') == 'a':
                subfield_a = subfield.text.strip() if subfield.text else ''
            elif subfield.get('code') == 'b':
                subfield_b = subfield.text.strip() if subfield.text else ''
        
        if subfield_a:
            title_parts = [subfield_a.rstrip(':').rstrip()]
            if subfield_b:
                title_parts.append(subfield_b)
            full_title = ' - '.join(title_parts)
            
            print(f'Subfield a: {subfield_a}')
            print(f'Subfield b: {subfield_b}')
            print(f'Kombinierter Titel: {full_title}')
            print(f'API-Titel (simuliert): Roter Stern über Deutschland - sowjetische Truppen in der DDR')
            print(f'Übereinstimmung: {full_title == "Roter Stern über Deutschland - sowjetische Truppen in der DDR"}')
