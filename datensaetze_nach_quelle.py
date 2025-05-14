import os
import xml.etree.ElementTree as ET

def split_by_quelle(input_file='voebvoll-20241027.xml', output_dir='nach_quelle'):
    os.makedirs(output_dir, exist_ok=True)
    handles = {}
    header_lines = []
    in_header = True
    buffer = []
    in_record = False

    def make_safe(name):
        safe = ''.join(c if c.isalnum() or c=='_' else '_' for c in name)
        return safe or 'unknown'

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
                        buffer = []
                        in_record = False
                        continue
                    quelle_vals = []
                    for df in elem.findall('datafield[@tag="040"]'):
                        for sf in df.findall('subfield'):
                            txt = sf.text.strip() if sf.text else ''
                            if txt:
                                quelle_vals.append(txt)
                    quelle = '_'.join(quelle_vals) if quelle_vals else 'unknown'
                    safe_q = make_safe(quelle)
                    if safe_q not in handles:
                        path = os.path.join(output_dir, f"{safe_q}.xml")
                        fh = open(path, 'w', encoding='utf-8')
                        for hl in header_lines:
                            fh.write(hl)
                        fh.write(f'<collection xmlns:marc="http://www.loc.gov/MARC21/slim">\n')
                        handles[safe_q] = fh
                    handles[safe_q].write(snippet)
                    buffer = []
                    in_record = False
            else:
                if line.lstrip().startswith('<record'):
                    in_record = True
                    buffer = [line]

    for fh in handles.values():
        fh.write('</collection>\n')
        fh.close()

if __name__ == '__main__':
    split_by_quelle()
