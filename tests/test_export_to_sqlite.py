import sqlite3
import textwrap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_to_sqlite import import_marc_to_db

SAMPLE_XML = textwrap.dedent(
    """
    <collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      <record>
        <leader>01234cam  2200277 a 4500</leader>
        <controlfield tag="001">A1</controlfield>
        <controlfield tag="008">991231s2005    nyu           ger</controlfield>
        <datafield tag="020" ind1=" " ind2=" ">
          <subfield code="a">1234567890</subfield>
        </datafield>
        <datafield tag="049" ind1=" " ind2=" ">
          <subfield code="a">DE-V0109</subfield>
        </datafield>
        <datafield tag="245" ind1="0" ind2="0">
          <subfield code="a">Title</subfield>
          <subfield code="b">Subtitle</subfield>
        </datafield>
        <datafield tag="260" ind1=" " ind2=" ">
          <subfield code="a">Berlin</subfield>
          <subfield code="b">TestPub</subfield>
          <subfield code="c">2005</subfield>
        </datafield>
      </record>
    </collection>
    """
).strip()


def test_import_marc_to_db(tmp_path: Path) -> None:
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")
    db_file = tmp_path / "test.db"

    import_marc_to_db(str(xml_file), str(db_file))

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("SELECT control_number FROM records")
    control_number = cur.fetchone()[0]
    assert control_number == "A1"

    cur.execute("SELECT isbn, title FROM record_main_data")
    row = cur.fetchone()
    assert row[0] == "1234567890"
    assert row[1] == "Title"

    cur.execute("SELECT COUNT(*) FROM libraries")
    assert cur.fetchone()[0] == 1

    conn.close()