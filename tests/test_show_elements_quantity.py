import csv
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from show_elements_quantity import parse_008_field, parse_marc21_quantity

SAMPLE_XML = textwrap.dedent(
    """
    <collection xmlns:marc="http://www.loc.gov/MARC21/slim">
    <record>
    <leader>01234cam  22002771i 4500</leader>
    <controlfield tag="001">D-i34533506180556</controlfield>
    <controlfield tag="007">ta</controlfield>
    <controlfield tag="008">991231s2005    nyuuun              ger</controlfield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">3453350618</subfield>
    </datafield>
    <datafield tag="040" ind1=" " ind2=" ">
      <subfield code="e">rak</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0202</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0913</subfield>
    </datafield>
    <datafield tag="100" ind1="0" ind2=" ">
      <subfield code="a">Krosigk, Esther von</subfield>
    </datafield>
    <datafield tag="245" ind1="0" ind2="4">
      <subfield code="a">Das Haus der Zeichen :</subfield>
      <subfield code="b">Roman</subfield>
      <subfield code="c">Esther von Krosigk</subfield>
    </datafield>
    <datafield tag="250" ind1=" " ind2=" ">
      <subfield code="a">Taschenbucherstausg.</subfield>
    </datafield>
    <datafield tag="260" ind1=" " ind2=" ">
      <subfield code="a">München</subfield>
      <subfield code="b">Heyne</subfield>
      <subfield code="c">2005</subfield>
    </datafield>
    <datafield tag="300" ind1=" " ind2=" ">
      <subfield code="a">556 S.</subfield>
    </datafield>
    <datafield tag="490" ind1="0" ind2="#">
      <subfield code="a">Heyne</subfield>
      <subfield code="v">35061 : Diana</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="5">
      <subfield code="a">Anhalt</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Gut &lt;Landwirtschaft&gt;</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Familie</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="4">
      <subfield code="a">Geschichte 1864-1945</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">Belletristische Darstellung</subfield>
    </datafield>
    <datafield tag="969" ind1="#" ind2="#">
      <subfield code="a">DE-B3Kat</subfield>
      <subfield code="6">D-1BV020845625</subfield>
    </datafield>
    </record>

    <record>
    <leader>01234cam  22002771i 4500</leader>
    <controlfield tag="001">D-i34427359120602</controlfield>
    <controlfield tag="007">ta</controlfield>
    <controlfield tag="008">991231s2006    nyuuun              ger</controlfield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">3442735912</subfield>
    </datafield>
    <datafield tag="040" ind1=" " ind2=" ">
      <subfield code="e">rak</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0109</subfield>
    </datafield>
    <datafield tag="100" ind1="0" ind2=" ">
      <subfield code="a">Kröhn, Julia</subfield>
    </datafield>
    <datafield tag="245" ind1="0" ind2="4">
      <subfield code="a">Die Chronistin :</subfield>
      <subfield code="b">Roman</subfield>
      <subfield code="c">Julia Kröhn</subfield>
    </datafield>
    <datafield tag="250" ind1=" " ind2=" ">
      <subfield code="a">Orig.-Ausg.</subfield>
    </datafield>
    <datafield tag="260" ind1=" " ind2=" ">
      <subfield code="a">München</subfield>
      <subfield code="b">Goldmann</subfield>
      <subfield code="c">2006</subfield>
    </datafield>
    <datafield tag="300" ind1=" " ind2=" ">
      <subfield code="a">602 S.</subfield>
    </datafield>
    <datafield tag="490" ind1="0" ind2="#">
      <subfield code="a">Goldmann</subfield>
      <subfield code="v">73591 : btb</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="5">
      <subfield code="a">Paris</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Geschichtsschreiberin</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Ordensschwester</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Heilerin</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="4">
      <subfield code="a">Geschichte 1190-1240</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">Belletristische Darstellung</subfield>
    </datafield>
    <datafield tag="969" ind1="#" ind2="#">
      <subfield code="a">DE-B3Kat</subfield>
      <subfield code="6">D-1BV021832379</subfield>
    </datafield>
    </record>

    <record>
    <leader>01234cam  22002771i 4500</leader>
    <controlfield tag="001">D-i97839380468690006</controlfield>
    <controlfield tag="007">z|</controlfield>
    <controlfield tag="008">991231s2008    nyuuun              ger</controlfield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">9783938046869</subfield>
    </datafield>
    <datafield tag="040" ind1=" " ind2=" ">
      <subfield code="e">rak</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0109</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0202</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-Eh4</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0508</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-513</subfield>
    </datafield>
    <datafield tag="245" ind1="0" ind2="4">
      <subfield code="a">Die Goldhändlerin</subfield>
      <subfield code="c">Iny Lorentz. Gelesen von Elke Schützhold. Tonregie: Gerlinde Engelhardt</subfield>
    </datafield>
    <datafield tag="260" ind1=" " ind2=" ">
      <subfield code="a">Berg</subfield>
      <subfield code="b">AME Hören</subfield>
      <subfield code="c">2008</subfield>
    </datafield>
    <datafield tag="300" ind1=" " ind2=" ">
      <subfield code="a">6 CDs (460 Min.) &amp; Faltbl.</subfield>
    </datafield>
    <datafield tag="700" ind1="0" ind2=" ">
      <subfield code="a">Lorentz, Iny</subfield>
    </datafield>
    <datafield tag="969" ind1="#" ind2="#">
      <subfield code="a">DE-B3Kat</subfield>
      <subfield code="6">D-1BV036457208</subfield>
    </datafield>
    </record>

    <record>
    <leader>01234cam  22002771i 4500</leader>
    <controlfield tag="001">D-i38702444370004</controlfield>
    <controlfield tag="007">z|</controlfield>
    <controlfield tag="008">991231s2006    nyuuun              ger</controlfield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">3870244437</subfield>
    </datafield>
    <datafield tag="040" ind1=" " ind2=" ">
      <subfield code="e">rak</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-V0512</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-1270</subfield>
    </datafield>
    <datafield tag="049" ind1=" " ind2=" ">
      <subfield code="a">DE-Sht10</subfield>
    </datafield>
    <datafield tag="245" ind1="0" ind2="0">
      <subfield code="a">Resturlaub</subfield>
      <subfield code="c">Tommy Jaud. Christoph Maria Herbst liest. [Regie: Frank Marienfeld]</subfield>
    </datafield>
    <datafield tag="246" ind1="1" ind2="3">
      <subfield code="a">Christoph Maria Herbst liest Tommy Jaud: Resturlaub</subfield>
    </datafield>
    <datafield tag="250" ind1=" " ind2=" ">
      <subfield code="a">Autorisierte Lesefassung</subfield>
    </datafield>
    <datafield tag="260" ind1=" " ind2=" ">
      <subfield code="a">Berlin</subfield>
      <subfield code="b">Argon-Verl.</subfield>
      <subfield code="c">2006</subfield>
    </datafield>
    <datafield tag="300" ind1=" " ind2=" ">
      <subfield code="a">4 CDs &amp; Booklet ([6] Bl.)</subfield>
    </datafield>
    <datafield tag="490" ind1="0" ind2="#">
      <subfield code="a">Argon-Hörbuch</subfield>
    </datafield>
    <datafield tag="700" ind1="0" ind2=" ">
      <subfield code="a">Jaud, Tommy</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="5">
      <subfield code="a">Bamberg</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Mann</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Alltag</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Überdruss</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">Belletristische Darstellung</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">CD</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="5">
      <subfield code="a">Bamberg</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="5">
      <subfield code="a">Buenos Aires</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Mann</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Lebenskrise</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2=" ">
      <subfield code="a">Aussteiger</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">Belletristische Darstellung</subfield>
    </datafield>
    <datafield tag="653" ind1=" " ind2="6">
      <subfield code="a">CD</subfield>
    </datafield>
    <datafield tag="969" ind1="#" ind2="#">
      <subfield code="a">DE-B3Kat</subfield>
      <subfield code="6">D-1BV022228988</subfield>
    </datafield>
    </record>

    </collection>
    """
).strip()

def test_parse_008_field():
    example = "991231s2005    nyuuun              ger"
    result = parse_008_field(example)
    assert result == {
        "Eingabedatum": "991231",
        "Publikationsstatus": "s (Einzelnes bekanntes Datum)",
        "Publikationsjahr_1": "2005",
        "Publikationsland": "nyu (New York (USA))",
        "Sprache": "ger (Deutsch)",
    }

def test_parse_marc21_quantity(tmp_path):
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    out_csv = tmp_path / "result.csv"
    parse_marc21_quantity(str(xml_file), str(out_csv))

    with open(out_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))

    header = rows[0]
    assert header == ["Element", "Beschreibung", "Anzahl Befüllung", "Befüllung in %"]

    data = {row[0]: row[2] for row in rows[1:]}
    assert data['<controlfield tag="001">'] == '4'
    assert data['<controlfield tag="008">'] == '4'
    assert data['<datafield tag="260" ind1=" " ind2=" ">'] == '4'

    # check details file
    details_csv = out_csv.with_name(out_csv.stem + "_008_details.csv")
    with open(details_csv, newline="", encoding="utf-8-sig") as f:
        details = list(csv.reader(f, delimiter=";"))
    assert details[1] == ['Eingabedatum', '4', '100.00%', '100.00%']
    assert details[2][0] == 'Publikationsstatus'
