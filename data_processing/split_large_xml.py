import xml.etree.ElementTree as ET

# Path to original file
xml_file = "voebvoll-20241027.xml"

# Name for the smaller test file
output_file = "test-teil_1.xml"

# Number of records in the test file
max_records = 10000  # e.g. 10,000 records

count = 0

print(f"Starte das Aufteilen von {xml_file} ...")

with open(output_file, "w", encoding="utf-8") as out:
    out.write("<collection>\n")  # Root tag for MARCXML file
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
