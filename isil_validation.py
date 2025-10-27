from lxml import etree
import requests
import re
import csv
import time
from tqdm import tqdm

# 1) XML-Datei einlesen
xml_file = "voebvoll-20241027.xml"
isil_codes = set()

# 2) ISIL-Codes extrahieren aus allen Records 
print("Starte Extraktion der ISIL-Codes ...")

context = etree.iterparse(xml_file, events=("end",), tag="record")

for _, record in tqdm(context, desc="Lese XML", unit="record"):
    for field in record.findall(".//datafield[@tag='049']"):
        for sub in field.findall(".//subfield[@code='a']"):
            if sub.text:
                code = sub.text.strip()
                if code.startswith("DE-"):
                    # 1. Entfernt 'V' oder 'V0' direkt nach 'DE-'
                    cleaned_code = re.sub(r"^DE-?V0?", "DE-", code)
                    isil_codes.add(cleaned_code)
    record.clear()
    while record.getprevious() is not None:
        del record.getparent()[0]

print(f"Anzahl unterschiedlicher ISIL-Codes gefunden: {len(isil_codes)}")

# 3) Überprüfen der Codes bei API
results = []
base_url = "https://sigel.staatsbibliothek-berlin.de/api/org/"

for code in tqdm(sorted(isil_codes), desc="Prüfe ISILs", unit="code"):
    bibliothek_name = None
    try:
        resp = requests.get(f"{base_url}{code}.jsonld", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            bibliothek_name = data.get("member", [{}])[0].get("name", "") if "member" in data else ""
            status = "VALID" if bibliothek_name else "UNKNOWN_NO_NAME"
        else:
            status = f"HTTP_{resp.status_code}"
    except Exception as e:
        status = f"ERROR_{str(e)}"
    results.append({"ISIL": code, "Status": status, "Name": bibliothek_name})
    time.sleep(0.05)  # kleine Pause für API-Stabilität

# 4) Ergebnisse in eine CSV schreiben
csv_file = "isil_matching_results.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["ISIL", "Status", "Name"])
    writer.writeheader()
    writer.writerows(results)

print("Fertig! Ergebnisse geschrieben nach:", csv_file)
