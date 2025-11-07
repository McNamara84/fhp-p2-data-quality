import xml.etree.ElementTree as ET

from marc_utils import percentage_of_records


def calculate_008_date_percentage(xml_file_path: str) -> float:
    """Return percentage of records whose 008 field starts with ``991231``."""

    def predicate(elem: ET.Element) -> bool:
        controlfield_008 = elem.find('./controlfield[@tag="008"]')
        return bool(controlfield_008 is not None and controlfield_008.text and controlfield_008.text.startswith('991231'))

    return percentage_of_records(xml_file_path, predicate)


if __name__ == '__main__':
    xml_file_path = 'voebvoll-20241027.xml'
    percentage = calculate_008_date_percentage(xml_file_path)
    print(f"Percentage of records with controlfield tag='008' starting '991231': {percentage:.2f}%")
