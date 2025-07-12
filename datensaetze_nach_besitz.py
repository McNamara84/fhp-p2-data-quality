import xml.etree.ElementTree as ET
from typing import Iterable

from marc_utils import split_records


def split_by_besitz(input_file: str = 'voebvoll-20241027.xml', output_dir: str = 'nach_besitz') -> None:
    """Split records by field 049 subfield ``a`` into separate files."""

    def extractor(elem: ET.Element) -> Iterable[str]:
        vals = []
        for df in elem.findall('datafield[@tag="049"]'):
            for sf in df.findall('subfield'):
                if sf.get('code') == 'a' and sf.text and sf.text.strip():
                    vals.append(sf.text.strip())
        return vals or ['unknown']

    split_records(input_file, output_dir, extractor)


if __name__ == '__main__':
    split_by_besitz()
