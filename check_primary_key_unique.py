import sys
import tkinter as tk
from tkinter import messagebox

from marc_utils import (
    DEFAULT_FILE_NAME,
    iter_records,
    get_controlfield_value,
)

def analyze_primary_key_unique(file_path: str):
    seen = set()
    duplicates = 0
    total = 0
    for elem in iter_records(file_path):
        value = get_controlfield_value(elem, "001")
        total += 1
        if value in seen:
            duplicates += 1
        else:
            seen.add(value)
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