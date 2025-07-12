import os
import xml.etree.ElementTree as ET
from typing import Callable, Iterable, List, Tuple

def make_safe_filename(name: str) -> str:
    """Return a filesystem-friendly version of ``name``."""
    safe = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    return safe or 'unknown'


def split_records(
    input_file: str,
    output_dir: str,
    extractor: Callable[[ET.Element], Iterable[str]],
) -> None:
    """Split ``input_file`` into multiple files using ``extractor`` to determine filenames."""
    os.makedirs(output_dir, exist_ok=True)
    handles: dict[str, any] = {}
    header_lines: List[str] = []
    in_header = True
    buffer: List[str] = []
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
                        buffer = []
                        in_record = False
                        continue

                    keys = list(extractor(elem)) or ['unknown']
                    for key in keys:
                        safe = make_safe_filename(key)
                        if safe not in handles:
                            path = os.path.join(output_dir, f"{safe}.xml")
                            fh = open(path, 'w', encoding='utf-8')
                            for hl in header_lines:
                                fh.write(hl)
                            fh.write('<collection xmlns:marc="http://www.loc.gov/MARC21/slim">\n')
                            handles[safe] = fh
                        handles[safe].write(snippet)

                    buffer = []
                    in_record = False
            else:
                if line.lstrip().startswith('<record'):
                    in_record = True
                    buffer = [line]

    for fh in handles.values():
        fh.write('</collection>\n')
        fh.close()


def count_matching_records(
    input_file: str,
    predicate: Callable[[ET.Element], bool],
) -> Tuple[int, int]:
    """Return total and matching record counts for ``predicate``."""
    total = 0
    matching = 0
    for _, elem in ET.iterparse(input_file, events=('end',)):
        if elem.tag == 'record':
            total += 1
            if predicate(elem):
                matching += 1
            elem.clear()
    return total, matching


def percentage_of_records(
    input_file: str,
    predicate: Callable[[ET.Element], bool],
) -> float:
    """Return the percentage of records for which ``predicate`` is True."""
    total, matching = count_matching_records(input_file, predicate)
    return (matching / total * 100) if total else 0.0
