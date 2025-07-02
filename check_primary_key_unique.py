import sys
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox


def analyze_primary_key_unique(file_path: str):
    ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
    seen = set()
    duplicates = 0
    total = 0
    for event, elem in ET.iterparse(file_path, events=("end",)):
        if (
            elem.tag.replace(f"{{{ns['marc']}}}", "") == "controlfield"
            and elem.get("tag") == "001"
        ):
            total += 1
            value = (elem.text or "").strip()
            if value in seen:
                duplicates += 1
            else:
                seen.add(value)
        elem.clear()
    return total, duplicates


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_NAME
    total, duplicates = analyze_primary_key_unique(file_path)

    if duplicates == 0:
        message = f"Alle {total} Prim\u00e4rschl\u00fcssel sind eindeutig."
    else:
        percent = (duplicates / total * 100) if total else 0
        message = (
            f"Nicht eindeutige Prim\u00e4rschl\u00fcssel: {duplicates} von {total} "
            f"({percent:.2f}%)"
        )

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Prim\u00e4rschl\u00fcssel-Check", message)


if __name__ == "__main__":
    main()