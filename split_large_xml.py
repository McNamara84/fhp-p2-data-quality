import xml.etree.ElementTree as ET

#  Pfad zur Originaldatei
xml_file = "voebvoll-20241027.xml"

# Name für die kleinere Test-Datei
output_file = "test-teil_1.xml"

# anzhal der Datensätze in der Test-Datei
max_records = 10000  # z. B. 10.000 Datensätze

count = 0

print(f"Starte das Aufteilen von {xml_file} ...")

with open(output_file, "w", encoding="utf-8") as out:
    out.write("<collection>\n")  # Root-Tag für MARCXML-Datei
    for event, elem in ET.iterparse(xml_file, events=("end",)):
        if elem.tag == "record":
            out.write(ET.tostring(elem, encoding="unicode"))
            count += 1
            if count >= max_records:
                break
            elem.clear()
    out.write("</collection>\n")

print(f"✅ {count} Datensätze in {output_file} gespeichert.")
print("Fertig!")
