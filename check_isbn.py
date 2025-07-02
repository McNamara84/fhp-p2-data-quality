import sys
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox
import urllib.request
import json
from typing import Callable, Tuple

DEFAULT_FILE_NAME = "voebvoll-20241027.xml"


def is_valid_isbn10(isbn: str) -> bool:
    if len(isbn) != 10:
        return False
    total = 0
    for i, char in enumerate(isbn):
        if char == "X" and i == 9:
            value = 10
        elif char.isdigit():
            value = int(char)
        else:
            return False
        total += value * (10 - i)
    return total % 11 == 0


def is_valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum((int(d) * (1 if i % 2 == 0 else 3)) for i, d in enumerate(isbn[:-1]))
    check = (10 - (total % 10)) % 10
    return check == int(isbn[-1])


def isbn_exists(isbn: str) -> bool:
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=10) as f:
            data = json.loads(f.read().decode())
        return bool(data)
    except Exception:
        return False


def analyze_isbn(file_path: str, isbn_exist_func: Callable[[str], bool] = isbn_exists) -> Tuple[int, int, int]:
    ns = {"marc": "http://www.loc.gov/MARC21/slim"}
    total_with_isbn = 0
    invalid_syntax = 0
    invalid_real = 0

    for event, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag.replace(f"{{{ns['marc']}}}", "") != "record":
            continue

        isbns = []
        for df in elem.findall('datafield[@tag="020"]'):
            for sf in df.findall('subfield'):
                if sf.get('code') == 'a' and sf.text:
                    isbns.append(sf.text.strip())

        if not isbns:
            elem.clear()
            continue

        total_with_isbn += 1
        syntax_ok = True
        exists_ok = True

        for raw in isbns:
            clean = raw.replace('-', '').replace(' ', '')
            if len(clean) == 10:
                if not is_valid_isbn10(clean):
                    syntax_ok = False
                else:
                    if not isbn_exist_func(clean):
                        exists_ok = False
            elif len(clean) == 13:
                if not is_valid_isbn13(clean):
                    syntax_ok = False
                else:
                    if not isbn_exist_func(clean):
                        exists_ok = False
            else:
                syntax_ok = False

        if not syntax_ok:
            invalid_syntax += 1
        elif not exists_ok:
            invalid_real += 1

        elem.clear()

    return total_with_isbn, invalid_syntax, invalid_real


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_NAME
    total, invalid_syntax, invalid_real = analyze_isbn(file_path)

    if invalid_syntax == 0 and invalid_real == 0:
        message = f"Alle {total} Datensätze mit ISBN sind korrekt."
    else:
        parts = []
        if invalid_syntax:
            percent = (invalid_syntax / total * 100) if total else 0
            parts.append(f"Syntaktisch inkorrekte ISBNs: {invalid_syntax} von {total} ({percent:.2f}%)")
        if invalid_real:
            percent = (invalid_real / total * 100) if total else 0
            parts.append(f"Nicht belegte ISBNs: {invalid_real} von {total} ({percent:.2f}%)")
        message = "\n".join(parts)

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("ISBN-Check", message)


if __name__ == "__main__":
    main()