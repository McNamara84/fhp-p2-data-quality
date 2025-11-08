import textwrap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_quality.check_primary_key import analyze_primary_key_unique

SAMPLE_XML = textwrap.dedent(
    """
    <collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      <record>
        <controlfield tag="001">A</controlfield>
      </record>
      <record>
        <controlfield tag="001">A</controlfield>
      </record>
      <record>
        <controlfield tag="001">B</controlfield>
      </record>
    </collection>
    """
).strip()


def test_analyze_primary_key_unique(tmp_path: Path) -> None:
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    total, duplicates = analyze_primary_key_unique(str(xml_file))

    assert total == 3
    assert duplicates == 1
