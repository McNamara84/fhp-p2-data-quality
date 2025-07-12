import textwrap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_duplicate_identifiers import analyze_identifier_duplicates

SAMPLE_XML = textwrap.dedent(
    """
    <collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">123</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">A</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">123</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">B</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">123</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">A</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="022" ind1=" " ind2=" ">
          <subfield code="a">ISSN1</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">X</subfield>
        </datafield>
      </record>
      <record>
        <datafield tag="022" ind1=" " ind2=" ">
          <subfield code="a">ISSN1</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">X</subfield>
        </datafield>
      </record>
    </collection>
    """
).strip()


def test_analyze_identifier_duplicates(tmp_path: Path) -> None:
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    (
        total_isbn,
        dup_isbn,
        real_isbn,
        total_issn,
        dup_issn,
        real_issn,
    ) = analyze_identifier_duplicates(str(xml_file))

    assert total_isbn == 3
    assert dup_isbn == 2
    assert real_isbn == 0
    assert total_issn == 2
    assert dup_issn == 1
    assert real_issn == 1