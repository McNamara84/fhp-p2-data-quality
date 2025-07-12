import textwrap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_isbn import (
    analyze_isbn,
    is_valid_isbn10,
    is_valid_isbn13,
)

SAMPLE_XML = textwrap.dedent(
    """
    <collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">3453350618</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">1234567890</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">9780306406157</subfield>
        </datafield>
      </record>
    </collection>
    """
).strip()


def test_isbn_validators() -> None:
    assert is_valid_isbn10("3453350618")
    assert not is_valid_isbn10("1234567890")
    assert is_valid_isbn13("9780306406157")
    assert not is_valid_isbn13("9780306406158")


def test_analyze_isbn(tmp_path: Path) -> None:
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    def dummy_exists(isbn: str) -> bool:
        return isbn != "9780306406157"

    total, invalid_syntax, invalid_real = analyze_isbn(str(xml_file), isbn_exist_func=dummy_exists)

    assert total == 3
    assert invalid_syntax == 1
    assert invalid_real == 1