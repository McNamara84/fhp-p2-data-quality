import os
import xml.etree.ElementTree as ET
from typing import Callable, Iterable, List, Tuple
from io import IOBase as IO

# Common MARC21 namespace and default file name
NS = {"marc": "http://www.loc.gov/MARC21/slim"}
DEFAULT_FILE_NAME = "voebvoll-20241027.xml"


def iter_records(file_path: str) -> Iterable[ET.Element]:
    """Yield every ``record`` element in ``file_path`` clearing it afterwards."""
    for _, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag.replace(f"{{{NS['marc']}}}", "") == "record":
            yield elem
            elem.clear()


def get_subfield_values(elem: ET.Element, tag: str, code: str) -> List[str]:
    """Return stripped text of all subfields ``code`` in ``tag``."""
    return [
        sf.text.strip()
        for df in elem.findall(f'datafield[@tag="{tag}"]')
        for sf in df.findall('subfield')
        if sf.get('code') == code and sf.text
    ]


def get_controlfield_value(elem: ET.Element, tag: str) -> str:
    field = elem.find(f'controlfield[@tag="{tag}"]')
    return field.text.strip() if field is not None and field.text else ""

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
    handles: dict[str, IO[str]] = {}
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
import os
import xml.etree.ElementTree as ET
from typing import Callable, Iterable, List, Tuple
from io import IOBase as IO

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
    handles: dict[str, IO[str]] = {}
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
