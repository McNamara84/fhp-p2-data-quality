import xml.etree.ElementTree as ET
import requests
import csv
import time

# 1) XML-Datei einlesen
xml_file = "test-teil_1.xml"
tree = ET.parse(xml_file)
root = tree.getroot()

isil_codes = set()

# 2) ISIL-Codes extrahieren aus allen Records
for record in root.findall(".//record"):
    for field in record.findall(".//datafield[@tag='049']"):
        for sub in field.findall(".//subfield[@code='a']"):
            if sub.text:
                code = sub.text.strip()
                if code.startswith("DE-"):
                    # Entfernt 'V0' z.B. DE-V0106 -> DE-106
                    cleaned_code = code.replace("V0", "")
                    isil_codes.add(cleaned_code)

print(f"Anzahl unterschiedlicher ISIL-Codes gefunden: {len(isil_codes)}")

# 3) Überprüfen der Codes bei API
results = []
base_url = "https://sigel.staatsbibliothek-berlin.de/api/org/"

for code in sorted(isil_codes):
    url = f"{base_url}{code}.jsonld"
    bibliothek_name = None 
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            bibliothek_name = data.get("member", [{}])[0].get("name", "") if "member" in data else ""
            status = "VALID" if bibliothek_name else "UNKNOWN_NO_NAME"
        else:
            status = f"HTTP_{resp.status_code}"
    except Exception as e:
        status = f"ERROR_{str(e)}"

    results.append({"ISIL": code, "Status": status, "Name": bibliothek_name if bibliothek_name else None})

    # Kleine Pause, um die API zu schonen
    time.sleep(0.2)

# 4) Ergebnisse in eine CSV schreiben
csv_file = "isil_matching_results.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["ISIL", "Status", "Name"])
    writer.writeheader()
    writer.writerows(results)

print("Fertig! Ergebnisse geschrieben nach:", csv_file)
