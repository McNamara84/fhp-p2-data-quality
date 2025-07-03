import sys
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox
import urllib.request
import json
from typing import Callable, Dict, Iterable, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    """Return ``True`` if the Google Books API knows the given ISBN."""

    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        with urllib.request.urlopen(url, timeout=5) as f:
            data = json.loads(f.read().decode())
        return data.get("totalItems", 0) > 0
    except Exception:
        return False


def _collect_isbns(
    file_path: str,
    ns: Dict[str, str],
) -> Tuple[int, int, Set[str]]:
    """Return ``total_with_isbn``, ``invalid_syntax`` and all unique valid ISBNs."""

    total_with_isbn = 0
    invalid_syntax = 0
    unique_valid: Set[str] = set()

    for _, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag.replace(f"{{{ns['marc']}}}", "") != "record":
            continue

        isbns = [
            sf.text.strip()
            for df in elem.findall('datafield[@tag="020"]')
            for sf in df.findall('subfield')
            if sf.get('code') == 'a' and sf.text
        ]

        if not isbns:
            elem.clear()
            continue

        total_with_isbn += 1
        syntax_ok = True

        for raw in isbns:
            clean = raw.replace('-', '').replace(' ', '')
            if len(clean) == 10 and is_valid_isbn10(clean):
                unique_valid.add(clean)
            elif len(clean) == 13 and is_valid_isbn13(clean):
                unique_valid.add(clean)
            else:
                syntax_ok = False

        if not syntax_ok:
            invalid_syntax += 1

        elem.clear()

    return total_with_isbn, invalid_syntax, unique_valid


def _check_exists_parallel(
    isbns: Iterable[str],
    isbn_exist_func: Callable[[str], bool],
    max_workers: int = 10,
) -> Dict[str, bool]:
    """Check ISBN existence in parallel and return a cache dict."""

    results: Dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        future_map = {exe.submit(isbn_exist_func, i): i for i in isbns}
        processed = 0
        total = len(future_map)
        for future in as_completed(future_map):
            isbn = future_map[future]
            try:
                results[isbn] = future.result()
            except Exception:
                results[isbn] = False
            processed += 1
            if processed % 1000 == 0 or processed == total:
                print(
                    f"Prüfe ISBN-Existenz: {processed}/{total}",
                    flush=True,
                )
    return results


def _count_invalid_real(
    file_path: str,
    ns: Dict[str, str],
    cache: Dict[str, bool],
    invalid_syntax: int,
    total_with_isbn: int,
) -> Tuple[int, int, int]:
    """Second pass that counts invalid_real while printing progress."""

    invalid_real = 0
    processed = 0

    for _, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag.replace(f"{{{ns['marc']}}}", "") != "record":
            continue

        isbns = [
            sf.text.strip()
            for df in elem.findall('datafield[@tag="020"]')
            for sf in df.findall('subfield')
            if sf.get('code') == 'a' and sf.text
        ]

        if not isbns:
            elem.clear()
            continue

        processed += 1
        syntax_ok = True
        valid_isbns: Set[str] = set()

        for raw in isbns:
            clean = raw.replace('-', '').replace(' ', '')
            if len(clean) == 10 and is_valid_isbn10(clean):
                valid_isbns.add(clean)
            elif len(clean) == 13 and is_valid_isbn13(clean):
                valid_isbns.add(clean)
            else:
                syntax_ok = False

        if syntax_ok and any(not cache.get(i, False) for i in valid_isbns):
            invalid_real += 1

        if processed % 1000 == 0 or processed == total_with_isbn:
            correct = processed - invalid_syntax - invalid_real
            print(
                f"Datensätze: {processed}/{total_with_isbn} | "
                f"korrekt: {correct} | "
                f"Syntaxfehler: {invalid_syntax} | "
                f"nicht belegt: {invalid_real}",
                flush=True,
            )

        elem.clear()

    return total_with_isbn, invalid_syntax, invalid_real


def analyze_isbn(
    file_path: str,
    isbn_exist_func: Callable[[str], bool] = isbn_exists,
) -> Tuple[int, int, int]:
    """Analyze ISBN syntax and existence.

    The XML file is processed in two passes. First all unique, syntactically
    valid ISBNs are collected. Their existence is then checked concurrently.
    During the second pass the numbers of valid and invalid ISBNs are printed
    as progress information.
    """

    ns = {"marc": "http://www.loc.gov/MARC21/slim"}

    total_with_isbn, invalid_syntax, unique_valid = _collect_isbns(file_path, ns)

    cache = _check_exists_parallel(unique_valid, isbn_exist_func)

    return _count_invalid_real(file_path, ns, cache, invalid_syntax, total_with_isbn)


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