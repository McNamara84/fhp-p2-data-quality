import xml.etree.ElementTree as ET
from typing import Iterable

from marc_utils import split_records


def split_by_quelle(input_file: str = 'voebvoll-20241027.xml', output_dir: str = 'nach_quelle') -> None:
    """Split records by field 040 values into separate files."""

    def extractor(elem: ET.Element) -> Iterable[str]:
        quelle_vals = []
        for df in elem.findall('datafield[@tag="040"]'):
            for sf in df.findall('subfield'):
                txt = sf.text.strip() if sf.text else ''
                if txt:
                    quelle_vals.append(txt)
        if quelle_vals:
            return ['_'.join(quelle_vals)]
        return ['unknown']

    split_records(input_file, output_dir, extractor)


if __name__ == '__main__':
    split_by_quelle()
