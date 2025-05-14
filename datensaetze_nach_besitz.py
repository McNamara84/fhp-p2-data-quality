import os
import xml.etree.ElementTree as ET


def split_by_besitz(input_file='voebvoll-20241027.xml', output_dir='nach_besitz'):
    """
    Liest eine MARC21-XML-Datei zeilenweise ein und splittet jeden <record>
    nach dem Feld 049 Subfield 'a' (Lokale Besitzinformation) in separate XML-Dateien.
    Die Dateien werden im Ordner 'nach_besitz' abgelegt und nach dem Wert der Besitzinfo benannt.
    """
    # Hilfsfunktion für sichere Dateinamen
    def make_safe(name):
        safe = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        return safe or 'unknown'

    # Zielverzeichnis vorbereiten
    os.makedirs(output_dir, exist_ok=True)
    handles = {}          # offene Datei-Handles pro Besitzinfo
    header_lines = []     # Kopf der Originaldatei (vor erstem <record>)
    in_header = True
    buffer = []           # Zwischenspeicher für einen Record
    in_record = False

    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            if in_header:
                if line.lstrip().startswith('<record'):
                    in_header = False
                    in_record = True
                    buffer = [line]
                else:
                    header_lines.append(line)
            elif in_record:
                buffer.append(line)
                if line.lstrip().startswith('</record'):
                    snippet = ''.join(buffer)
                    try:
                        elem = ET.fromstring(snippet)
                    except ET.ParseError:
                        # Ungültiger Record: überspringen
                        buffer = []
                        in_record = False
                        continue

                    # Alle Besitzinformationen sammeln (Subfield code='a' bei tag 049)
                    besitz_vals = []
                    for df in elem.findall('datafield[@tag="049"]'):
                        for sf in df.findall('subfield'):
                            if sf.get('code') == 'a' and sf.text and sf.text.strip():
                                besitz_vals.append(sf.text.strip())

                    # Falls keine Besitzinfo, verwende 'unknown'
                    if not besitz_vals:
                        besitz_vals = ['unknown']

                    # Record für jede Besitzinfo schreiben
                    for val in besitz_vals:
                        safe = make_safe(val)
                        if safe not in handles:
                            # Neue Datei anlegen und Header schreiben
                            path = os.path.join(output_dir, f"{safe}.xml")
                            fh = open(path, 'w', encoding='utf-8')
                            for hl in header_lines:
                                fh.write(hl)
                            fh.write(f'<collection xmlns:marc="http://www.loc.gov/MARC21/slim">\n')
                            handles[safe] = fh
                        handles[safe].write(snippet)

                    # Reset für nächsten Record
                    buffer = []
                    in_record = False
            else:
                if line.lstrip().startswith('<record'):
                    in_record = True
                    buffer = [line]
                # sonst: Zeilen zwischen Records ignorieren

    # Abschluss: </collection> hinzufügen und Dateien schließen
    for fh in handles.values():
        fh.write('</collection>\n')
        fh.close()


if __name__ == '__main__':
    split_by_besitz()
