import sys
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Set, Tuple

from marc_utils import (
    DEFAULT_FILE_NAME,
    iter_records,
    get_subfield_values,
)


def analyze_identifier_duplicates(
    file_path: str,
) -> Tuple[int, int, int, int, int, int]:
    """Return statistics about duplicate ISBNs and ISSNs.

    The returned tuple contains:
        total number of ISBNs,
        number of duplicate ISBN occurrences,
        number of real ISBN duplicates (same holdings),
        total number of ISSNs,
        number of duplicate ISSN occurrences,
        number of real ISSN duplicates (same holdings).
    """
    isbn_data: Dict[str, List[Set[str]]] = {}
    issn_data: Dict[str, List[Set[str]]] = {}
    dup_isbn = 0
    dup_issn = 0
    total_isbn = 0
    total_issn = 0

    for elem in iter_records(file_path):
        isbns = get_subfield_values(elem, "020", "a")
        issns = get_subfield_values(elem, "022", "a")
        total_isbn += len(isbns)
        total_issn += len(issns)
        holdings = set(get_subfield_values(elem, "049", "a"))

        for isbn in isbns:
            if isbn in isbn_data:
                dup_isbn += 1
                isbn_data[isbn].append(holdings)
            else:
                isbn_data[isbn] = [holdings]

        for issn in issns:
            if issn in issn_data:
                dup_issn += 1
                issn_data[issn].append(holdings)
            else:
                issn_data[issn] = [holdings]


    real_isbn_count = sum(
        1
        for sets in isbn_data.values()
        if len(sets) > 1 and len({frozenset(s) for s in sets}) == 1
    )
    real_issn_count = sum(
        1
        for sets in issn_data.values()
        if len(sets) > 1 and len({frozenset(s) for s in sets}) == 1
    )

    return (
        total_isbn,
        dup_isbn,
        real_isbn_count,
        total_issn,
        dup_issn,
        real_issn_count,
    )


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_NAME
    (
        total_isbn,
        dup_isbn,
        real_isbn,
        total_issn,
        dup_issn,
        real_issn,
    ) = analyze_identifier_duplicates(file_path)

    lines = []
    if total_isbn:
        percent = dup_isbn / total_isbn * 100
        lines.append(f"Doppelte ISBNs: {dup_isbn} von {total_isbn} ({percent:.2f}%)")
        if real_isbn:
            percent_real = real_isbn / total_isbn * 100
            lines.append(
                f"Echte ISBN-Dubletten: {real_isbn} von {total_isbn} ({percent_real:.2f}%)"
            )
    if total_issn:
        percent = dup_issn / total_issn * 100
        lines.append(f"Doppelte ISSNs: {dup_issn} von {total_issn} ({percent:.2f}%)")
        if real_issn:
            percent_real = real_issn / total_issn * 100
            lines.append(
                f"Echte ISSN-Dubletten: {real_issn} von {total_issn} ({percent_real:.2f}%)"
            )

    message = "\n".join(lines) if lines else "Keine ISBN/ISSN gefunden."

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("ISBN/ISSN-Dubletten", message)


if __name__ == "__main__":
    main()import sys
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Set, Tuple

DEFAULT_FILE_NAME = "voebvoll-20241027.xml"


def analyze_identifier_duplicates(
    file_path: str,
) -> Tuple[int, int, int, int, int, int]:
    """Return statistics about duplicate ISBNs and ISSNs.

    The returned tuple contains:
        total number of ISBNs,
        number of duplicate ISBN occurrences,
        number of real ISBN duplicates (same holdings),
        total number of ISSNs,
        number of duplicate ISSN occurrences,
        number of real ISSN duplicates (same holdings).
    """
    ns = {"marc": "http://www.loc.gov/MARC21/slim"}
    isbn_data: Dict[str, List[Set[str]]] = {}
    issn_data: Dict[str, List[Set[str]]] = {}
    dup_isbn = 0
    dup_issn = 0
    total_isbn = 0
    total_issn = 0

    for _, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag.replace(f"{{{ns['marc']}}}", "") != "record":
            continue

        isbns = [
            sf.text.strip()
            for df in elem.findall('datafield[@tag="020"]')
            for sf in df.findall('subfield')
            if sf.get('code') == 'a' and sf.text
        ]
        issns = [
            sf.text.strip()
            for df in elem.findall('datafield[@tag="022"]')
            for sf in df.findall('subfield')
            if sf.get('code') == 'a' and sf.text
        ]
        total_isbn += len(isbns)
        total_issn += len(issns)
        holdings = {
            sf.text.strip()
            for df in elem.findall('datafield[@tag="049"]')
            for sf in df.findall('subfield')
            if sf.get('code') == 'a' and sf.text
        }

        for isbn in isbns:
            if isbn in isbn_data:
                dup_isbn += 1
                isbn_data[isbn].append(holdings)
            else:
                isbn_data[isbn] = [holdings]

        for issn in issns:
            if issn in issn_data:
                dup_issn += 1
                issn_data[issn].append(holdings)
            else:
                issn_data[issn] = [holdings]

        elem.clear()

    real_isbn_count = sum(
        1
        for sets in isbn_data.values()
        if len(sets) > 1 and len({frozenset(s) for s in sets}) == 1
    )
    real_issn_count = sum(
        1
        for sets in issn_data.values()
        if len(sets) > 1 and len({frozenset(s) for s in sets}) == 1
    )

    return (
        total_isbn,
        dup_isbn,
        real_isbn_count,
        total_issn,
        dup_issn,
        real_issn_count,
    )


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_NAME
    (
        total_isbn,
        dup_isbn,
        real_isbn,
        total_issn,
        dup_issn,
        real_issn,
    ) = analyze_identifier_duplicates(file_path)

    lines = []
    if total_isbn:
        percent = dup_isbn / total_isbn * 100
        lines.append(f"Doppelte ISBNs: {dup_isbn} von {total_isbn} ({percent:.2f}%)")
        if real_isbn:
            percent_real = real_isbn / total_isbn * 100
            lines.append(
                f"Echte ISBN-Dubletten: {real_isbn} von {total_isbn} ({percent_real:.2f}%)"
            )
    if total_issn:
        percent = dup_issn / total_issn * 100
        lines.append(f"Doppelte ISSNs: {dup_issn} von {total_issn} ({percent:.2f}%)")
        if real_issn:
            percent_real = real_issn / total_issn * 100
            lines.append(
                f"Echte ISSN-Dubletten: {real_issn} von {total_issn} ({percent_real:.2f}%)"
            )

    message = "\n".join(lines) if lines else "Keine ISBN/ISSN gefunden."

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("ISBN/ISSN-Dubletten", message)


if __name__ == "__main__":
    main()