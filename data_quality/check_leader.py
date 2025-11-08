import xml.etree.ElementTree as ET
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utilities.marc_utils import percentage_of_records


def calculate_leader_01234cam_percentage(xml_file_path: str) -> float:
    """Return percentage of records with leader starting ``01234cam``."""

    def predicate(elem: ET.Element) -> bool:
        leader = elem.find('leader')
        return bool(leader is not None and leader.text and leader.text.startswith('01234cam'))

    return percentage_of_records(xml_file_path, predicate)


if __name__ == '__main__':
    xml_file_path = 'voebvoll-20241027.xml'
    percentage = calculate_leader_01234cam_percentage(xml_file_path)
    print(f"Percentage of records with leader starting '01234cam': {percentage:.2f}%")
